# app/bot/utils/tg.py
from aiogram.exceptions import TelegramBadRequest
from app.core.logger import logger

async def safe_cb_answer(cb, text: str | None = None, show_alert: bool = False) -> None:
    try:
        await cb.answer(text=text, show_alert=show_alert, cache_time=0)
    except TelegramBadRequest:
        # query уже протух — это не критично, просто не шумим
        logger.debug("safe_cb_answer: TelegramBadRequest (too old/invalid query id)")
    except Exception as e:
        logger.warning(f"safe_cb_answer: unexpected error: {e}")
