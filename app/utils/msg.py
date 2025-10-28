# from aiogram.exceptions import TelegramBadRequest
# from aiogram.types import CallbackQuery


# async def edit_or_send(
#     cb: CallbackQuery,
#     text: str,
#     reply_markup=None,
#     parse_mode: str | None = None,
# ):
#     """
#     Редактирует caption для сообщений с медиа, иначе text.
#     Если редактирование невозможно (no text to edit, старая дата и т.д.) — шлёт новое сообщение.
#     """
#     msg = cb.message
#     try:
#         if getattr(msg, "photo", None) or getattr(msg, "video", None) or getattr(msg, "animation", None) or getattr(msg, "document", None):
#             # Сообщение с медиа — редактируем подпись
#             await msg.edit_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
#         else:
#             await msg.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
#     except TelegramBadRequest:
#         # Не получилось отредактировать — присылаем новое
#         await msg.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from aiogram.enums import ParseMode   # ⟵ добавь

async def edit_or_send(
    cb: CallbackQuery,
    text: str,
    reply_markup=None,
    parse_mode: str | None = None,
):
    """
    Редактирует caption для сообщений с медиа, иначе text.
    Если редактирование невозможно — шлёт новое сообщение.
    """
    # ВСЕГДА HTML по умолчанию
    if parse_mode is None:
        parse_mode = ParseMode.HTML

    msg = cb.message
    try:
        if getattr(msg, "photo", None) or getattr(msg, "video", None) or getattr(msg, "animation", None) or getattr(msg, "document", None):
            await msg.edit_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await msg.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    except TelegramBadRequest:
        await msg.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
