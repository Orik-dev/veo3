# from __future__ import annotations

# import secrets
# from aiogram import Router, Dispatcher, F
# from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
# from sqlalchemy import select, update, func
# from sqlalchemy.ext.asyncio import AsyncSession

# from app.core.db import SessionLocal
# from app.core.logger import logger
# from app.core.settings import settings
# from app.bot.init import bot
# from app.utils.msg import edit_or_send
# from app.utils.tg import safe_cb_answer
# from app.domain.users.service import get_or_create_user
# from app.models.models import User  # <- предполагаемая модель пользователя

# router = Router(name=__name__)

# REF_PREFIX = "ref_"

# def register_invite_handlers(dp: Dispatcher) -> None:
#     dp.include_router(router)

# async def _ensure_ref_code(session: AsyncSession, user: User) -> str:
#     """
#     Если у пользователя нет referral_code — создаём и сохраняем.
#     """
#     code = getattr(user, "referral_code", None)
#     if not code:
#         # короткий код: 10 символов [a-z0-9]
#         code = secrets.token_hex(5)
#         await session.execute(
#             update(User)
#             .where(User.user_id == user.user_id)
#             .values(referral_code=code)
#         )
#         await session.commit()
#     return code

# async def _invited_count(session: AsyncSession, inviter_user_id: int) -> int:
#     q = select(func.count()).where(User.invited_by == inviter_user_id)
#     return (await session.execute(q)).scalar_one()

# @router.message(F.text == "/invite_friend")
# async def cmd_invite_friend(msg: Message):
#     async with SessionLocal() as session:
#         me = await bot.get_me()
#         u = await get_or_create_user(session, msg.from_user.id)
#         code = await _ensure_ref_code(session, u)

#         deep_link = f"https://t.me/{me.username}?start={REF_PREFIX}{code}"

#         invited = await _invited_count(session, u.user_id)
#         bonus = getattr(settings, "REFERRAL_BONUS_CREDITS", 1)

#         kb = InlineKeyboardMarkup(inline_keyboard=[
#             [InlineKeyboardButton(text="🔗 Открыть ссылку", url=deep_link)],
#             [InlineKeyboardButton(text="🏠 Главная", callback_data="menu:root")],
#         ])

#         text = (
#             "🎁 Пригласите друзей и получите бонусы!\n\n"
#             f"• За каждого друга: +{bonus} генерация на баланс\n"
#             f"• Ваша ссылка: {deep_link}\n\n"
#             f"👥 Уже пригласили: {invited}"
#         )
#         await msg.answer(text, reply_markup=kb, disable_web_page_preview=True)

# @router.callback_query(F.data == "menu:invite")
# async def menu_invite(cb: CallbackQuery):
#     async with SessionLocal() as session:
#         me = await bot.get_me()
#         u = await get_or_create_user(session, cb.from_user.id)
#         code = await _ensure_ref_code(session, u)
#         deep_link = f"https://t.me/{me.username}?start={REF_PREFIX}{code}"
#         invited = await _invited_count(session, u.user_id)
#         bonus = getattr(settings, "REFERRAL_BONUS_CREDITS", 1)

#         kb = InlineKeyboardMarkup(inline_keyboard=[
#             [InlineKeyboardButton(text="🔗 Открыть ссылку", url=deep_link)],
#             [InlineKeyboardButton(text="🏠 Главная", callback_data="menu:root")],
#         ])
#         await edit_or_send(
#             cb,
#             "🎁 Пригласите друзей и получите бонусы!\n\n"
#             f"• За каждого друга: +{bonus} генерация на баланс\n"
#             f"• Ваша ссылка: {deep_link}\n\n"
#             f"👥 Уже пригласили: {invited}",
#             reply_markup=kb,
#         )
#         await safe_cb_answer(cb)

# # ---------- хелпер для учёта рефералки на /start ----------
# async def apply_referral_on_start(msg: Message) -> None:
#     """
#     ВСТАВЬТЕ вызов в самый верх вашего /start-хендлера:
#         await apply_referral_on_start(message)

#     Логика:
#     - парсим payload '/start ref_xxx'
#     - если новый пользователь ещё без invited_by — привяжем, начислим бонус инвайтеру
#     """
#     payload = ""
#     if msg.text and " " in msg.text:
#         payload = msg.text.split(" ", 1)[1].strip()

#     if not payload.startswith(REF_PREFIX):
#         return

#     code = payload[len(REF_PREFIX):].strip()
#     if not code:
#         return

#     async with SessionLocal() as session:
#         invited = await get_or_create_user(session, msg.from_user.id)

#         # уже привязан — ничего не делаем
#         if getattr(invited, "invited_by", None):
#             return

#         # найти инвайтера по коду
#         row = await session.execute(select(User).where(User.referral_code == code))
#         inviter = row.scalars().first()
#         if not inviter:
#             return

#         # нельзя реферить себя
#         if inviter.user_id == invited.user_id:
#             return

#         # привязываем и начисляем бонус
#         bonus = getattr(settings, "REFERRAL_BONUS_CREDITS", 1)

#         await session.execute(
#             update(User).where(User.user_id == invited.user_id).values(invited_by=inviter.user_id)
#         )
#         await session.execute(
#             update(User).where(User.user_id == inviter.user_id).values(credits=User.credits + bonus)
#         )
#         await session.commit()

#         try:
#             await bot.send_message(
#                 inviter.telegram_id,
#                 f"🎉 По вашей ссылке пришёл новый пользователь! +{bonus} генерация на баланс."
#             )
#         except Exception:
#             logger.exception("failed to notify inviter")
