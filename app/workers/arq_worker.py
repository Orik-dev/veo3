from __future__ import annotations

import asyncio
import httpx
from typing import Any, Sequence
import contextlib
from arq import run_worker, cron
from arq.connections import RedisSettings
from sqlalchemy import select, update, func, text, delete
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest, TelegramRetryAfter

from app.core.settings import settings
from app.core.logger import logger
from app.core.db import SessionLocal, engine
from app.bot.init import bot
from app.models.models import VideoRequest
from app.domain.generation.service_start import _refund_credits

# ✅ ИМПОРТИРУЕМ ФУНКЦИЮ ИЗ ОТДЕЛЬНОГО ФАЙЛА
from app.workers.broadcast import broadcast_send
async def process_runblob_result(ctx: dict[str, Any], runblob_task_id: str, success: bool, video_url: str | None):
    # (опционально) проверим доступность URL
    if success and video_url:
        try:
            async with httpx.AsyncClient(timeout=20) as cl:
                r = await cl.head(video_url, follow_redirects=True)
                r.raise_for_status()
        except Exception:
            logger.exception("HEAD video_url failed; keep URL as-is")

    async with SessionLocal() as session:
        st = "success" if success else "error"
        await session.execute(
            update(VideoRequest)
            .where(VideoRequest.task_id == str(runblob_task_id))
            .where(VideoRequest.status.in_(("pending", "processing")))
            .values(status=st, video_url=video_url if success else None)
        )
        await session.commit()

    logger.info(f"post-process done: task_id={runblob_task_id} success={success}")


async def reconcile_stuck(ctx: dict[str, Any]):
    """
    Найти слишком долгие 'pending'/'processing' задачи, пометить 'error',
    вернуть кредиты и уведомить пользователя.
    Используем MySQL NOW() - INTERVAL 20 MINUTE, чтобы не ловить TZ.
    """
    async with SessionLocal() as session:
        q = select(VideoRequest.id).where(
            VideoRequest.status.in_(("pending", "processing")),
            VideoRequest.created_at < func.date_sub(func.now(), text("INTERVAL 20 MINUTE")),
        )
        rows: Sequence[tuple] = (await session.execute(q)).all()
        stuck_ids = [row[0] for row in rows]
        if not stuck_ids:
            return

        await session.execute(
            update(VideoRequest)
            .where(VideoRequest.id.in_(stuck_ids))
            .values(status="error")
        )
        await session.commit()
        logger.warning(f"reconciled stuck tasks (set to error): {stuck_ids}")

        # Уведомить и вернуть кредиты всем «застрявшим»
        res = await session.execute(select(VideoRequest).where(VideoRequest.id.in_(stuck_ids)))
        stuck_reqs = res.scalars().all()
        for vr in stuck_reqs:
            try:
                if vr.cost and vr.cost > 0:
                    await _refund_credits(session, vr.user_id, vr.cost)
            except Exception:
                logger.exception("reconcile_stuck: refund failed id=%s", vr.id)
            try:
                await bot.send_message(
                    vr.chat_id,
                    "❌ Превышено время обработки.\n\n"
                    f"💸 Возвращено: {vr.cost} генераций.\n"
                    "🛠 Попробуйте изменить описание (промт) или прикрепить другое фото."
                )
            except Exception:
                logger.exception("reconcile_stuck: notify failed id=%s", vr.id)


async def startup(ctx: dict[str, Any]):
    logger.info("🚀 ARQ Worker startup: ping DB")
    from sqlalchemy import text as sql_text
    async with engine.begin() as conn:
        await conn.execute(sql_text("SELECT 1"))
    ctx["ready"] = True


async def shutdown(ctx: dict[str, Any]):
    logger.info("🔻 ARQ Worker shutdown")


class WorkerSettings:
    functions = [
        process_runblob_result,
        reconcile_stuck,
        broadcast_send,
    ]
    cron_jobs = [
        cron(reconcile_stuck, minute={0, 10, 20, 30, 40, 50}),
    ]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    on_startup = startup
    on_shutdown = shutdown
    burst = False
    
    job_timeout = 259200          # 12 часов (достаточно для 1M при 25 RPS)
    keep_result = 86400          # храним результат 24 часа
    max_jobs = 10 


if __name__ == "__main__":
    asyncio.run(run_worker(WorkerSettings))
