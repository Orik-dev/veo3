from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, select
from sqlalchemy.engine import Result

from app.models.models import VideoRequest
from app.core.logger import logger
from app.domain.generation.service_start import _refund_credits


def _to_status_flag(status: str) -> str:
    ok_vals = {"completed", "success", "done", "ok", "true"}
    return "success" if (status or "").lower() in ok_vals else "error"


async def finalize_by_callback(
    session: AsyncSession,
    *,
    runblob_task_id: str,
    status: str,
    url: str | None
) -> bool:
    """
    Помечает задачу по коллбэку. При error — инициирует возврат кредитов,
    т.к. на старте они уже были списаны.
    """
    st = _to_status_flag(status)

    upd = (
        update(VideoRequest)
        .where(VideoRequest.task_id == runblob_task_id)
        .where(VideoRequest.status.in_(("pending", "processing")))
        .values(
            status=st,
            video_url=url if st == "success" else None,
        )
    )

    result: Result = await session.execute(upd)
    await session.commit()

    updated = (result.rowcount or 0) > 0
    if not updated:
        return False

    # При финальном провале — вернуть кредиты пользователю
    if st == "error":
        try:
            vr: VideoRequest | None = (
                (await session.execute(select(VideoRequest).where(VideoRequest.task_id == runblob_task_id)))
                .scalars()
                .first()
            )
            if vr and vr.cost and vr.cost > 0:
                await _refund_credits(session, vr.user_id, vr.cost)
        except Exception:
            logger.exception("finalize_by_callback: refund on error failed (task_id=%s)", runblob_task_id)

    return True

