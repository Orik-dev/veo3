from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert
from app.models.models import VideoRequest
from app.domain.users.service import get_or_create_user, deduct_credits_atomic
from app.core.settings import settings
from app.core.logger import logger
from .clients import runblob
from app.domain.generation.clients.runblob import RunBlobError
from app.domain.generation.error import GenerationError
import uuid
import random  # ← NEW


def task_callback_url(local_task_id: str) -> str:
    base = settings.webhook_base().rstrip("/")
    return f"{base}/webhook/runblob?task={local_task_id}&token={settings.WEBHOOK_SECRET}"


async def _refund_credits(session: AsyncSession, user_id: int, amount: int) -> None:
    # делаем возврат атомарно через сервис пользователей (если есть) или простым апдейтом
    from sqlalchemy import update
    from app.models.models import User
    await session.execute(
        update(User)
        .where(User.user_id == user_id)
        .values(credits=User.credits + amount)
    )
    await session.commit()


async def start_generation(
    session: AsyncSession,
    *,
    telegram_id: int,
    prompt: str,
    model: str,
    aspect_ratio: str,
    bytes_image_b64: str | None
) -> str:
    user = await get_or_create_user(session, telegram_id)
    if model == "veo-3-fast":
        cost = settings.COST_CREDITS_FAST
    else:
        cost = settings.COST_CREDITS_QUALITY

    ok = await deduct_credits_atomic(session, user.user_id, cost)
    if not ok:
        raise GenerationError("INSUFFICIENT_CREDITS")

    cb = task_callback_url(str(telegram_id))

    # ── NEW: случайный seed для детерминированности внутри одной генерации ──
    seed = random.randint(1, 10000)
    logger.info("start_generation: tg=%s seed=%s model=%s ar=%s", telegram_id, seed, model, aspect_ratio)

    try:
        data = await runblob.generate(
            prompt=prompt,
            model_type=model,            # "veo-3-fast" | "veo-3-quality"
            aspect_ratio=aspect_ratio,
            callback_url=cb,
            bytes_image_b64=bytes_image_b64,
            seed=seed,                   # ← передаём seed
            raise_for_status=True,
        )
    except RunBlobError as e:
        # вернуть кредиты, если не ушли в работу
        try:
            await _refund_credits(session, user.user_id, cost)
        except Exception as refund_err:
            logger.error("refund_credits_failed user=%s cost=%s err=%s", user.user_id, cost, refund_err)
        logger.warning("runblob_start_failed tg=%s code=%s detail=%s", telegram_id, e.code, e.message)
        raise GenerationError(e.code, technical=e.message)

    runblob_id = data["task_id"]
    local_id = str(uuid.uuid4())
    await session.execute(
        insert(VideoRequest).values(
            id=local_id,
            user_id=user.user_id,
            chat_id=telegram_id,
            prompt=prompt,
            format=aspect_ratio,
            model=model,
            cost=cost,
            status="pending",
            task_id=runblob_id,
            # Если у вас есть колонка `seed` в VideoRequest — раскомментируйте следующую строку:
            # seed=seed,
        )
    )
    await session.commit()
    logger.info("start_generation: tg=%s runblob=%s", telegram_id, runblob_id)
    return runblob_id
