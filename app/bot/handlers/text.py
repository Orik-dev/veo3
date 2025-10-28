from __future__ import annotations

from aiogram import Router, F, Dispatcher
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from app.core.db import SessionLocal
from app.core.logger import logger
from app.core.settings import settings

from app.bot.i18n import t, _load_locales, get_user_lang
from app.bot.keyboards.common import kb_vertical_toggle
from app.utils.msg import edit_or_send
from app.utils.tg import safe_cb_answer
from app.domain.generation.service_start import start_generation
from app.domain.users.service import get_or_create_user
from app.domain.generation.error import GenerationError, to_user_message
from app.bot.handlers.start import on_start, on_menu_cmd, on_create_video

router = Router(name=__name__)


def register_text_handlers(dp: Dispatcher) -> None:
    dp.include_router(router)


async def _session() -> AsyncSession:
    return SessionLocal()


class T2V(StatesGroup):
    waiting_prompt = State()   # ждём промт в одном сообщении


async def _strings(session: AsyncSession, user_id: int) -> dict[str, str]:
    lang = await get_user_lang(session, user_id)
    return _load_locales()[lang]

@router.message(T2V.waiting_prompt, F.text.regexp(r"^/start(?:@.+)?$"))
async def _cmd_start_in_t2v(msg: Message, state: FSMContext):
    await state.clear()
    await on_start(msg)

@router.message(T2V.waiting_prompt, F.text.regexp(r"^/(?:menu|create_video)(?:@.+)?$"))
async def _cmd_other_in_t2v(msg: Message, state: FSMContext):
    await state.clear()
    if msg.text.startswith("/menu"):
        await on_menu_cmd(msg)
    else:
        await on_create_video(msg)


# ─────────────────────────────────────────────────────────────
# Вход в режим «текст→видео» с ТУМБЛЕРОМ формата (как в image)
# ─────────────────────────────────────────────────────────────
@router.callback_query(F.data == "menu:text")
async def menu_text(cb: CallbackQuery, state: FSMContext):
    async with SessionLocal() as session:
        await state.clear()

        # ранняя проверка баланса
        user = await get_or_create_user(session, cb.from_user.id)
        bal = user.credits
        needed = settings.COST_CREDITS_QUALITY
        if bal < needed:
            price = Decimal(settings.SUBSCRIPTION_PLANS_RUBS.get("test", {}).get("price", 0))
            await edit_or_send(
                cb,
                "❌ У вас не достаточно генераций(",
                # f"Баланс: {bal}\nНужно: {needed}" + (f"\nСтоимость 1 видео: {price:.0f} ₽" if price else ""),
            )
            await safe_cb_answer(cb)
            return

        # по умолчанию 9:16, тумблер переключает на 16:9
        await state.update_data(ar="9:16", model="veo-3-quality")
        await edit_or_send(
            cb,
            "✍🏻 Введите описание видео для генерации",
            reply_markup=kb_vertical_toggle(is_vertical=True),
        )
        await state.set_state(T2V.waiting_prompt)
        await safe_cb_answer(cb)


# Переключатель 9:16 ↔ 16:9
@router.callback_query(T2V.waiting_prompt, F.data == "toggle:ar")
async def toggle_ar(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    ar = data.get("ar", "9:16")
    new_ar = "16:9" if ar == "9:16" else "9:16"
    await state.update_data(ar=new_ar)
    is_vertical = (new_ar == "9:16")
    await edit_or_send(
        cb,
        "✍🏻 Введите описание видео для генерации",
        reply_markup=kb_vertical_toggle(is_vertical=is_vertical),
    )
    await safe_cb_answer(cb)


# Защита от вложений
@router.message(T2V.waiting_prompt, F.photo)
async def photo_in_text_mode(msg: Message, state: FSMContext):
    await msg.answer("❌ Генерация по фото не доступна в режиме текста, попробуйте ещё раз:")

@router.message(T2V.waiting_prompt, F.document)
async def document_in_text_mode(msg: Message, state: FSMContext):
    await msg.answer("❌ Нельзя прикреплять файлы, попробуйте ещё раз:")

@router.message(T2V.waiting_prompt, F.video)
async def video_in_text_mode(msg: Message, state: FSMContext):
    await msg.answer("❌ Нельзя прикрепить видео, попробуйте ещё раз:")


# Принимаем промт, но НЕ команды
@router.message(T2V.waiting_prompt, F.text, ~F.text.regexp(r"^/"))
async def set_prompt(msg: Message, state: FSMContext):
    txt = (msg.text or "").strip()
    if len(txt) > 2000:
        await msg.answer("❌ Описание слишком длинное. Максимум 2000 символов.")
        return
    if len(txt) < 5:
        await msg.answer("❌ Описание слишком короткое. Минимум 5 символов.")
        return

    async with SessionLocal() as session:
        data = await state.get_data()
        if not data.get("model"):
            await msg.answer("❌ Ошибка: не выбрана модель генерации")
            return

        await state.update_data(prompt=txt)
        ar = data.get("ar", "9:16")

        # «Отправляем…»
        processing_msg = await msg.answer("🔄 Отправляем запрос на генерацию…")

        user = await get_or_create_user(session, msg.from_user.id)
        bal_before = user.credits

        try:
            task_id = await start_generation(
                session=session,
                telegram_id=msg.from_user.id,
                prompt=txt,
                model=data["model"],
                aspect_ratio=ar,
                bytes_image_b64=None,
            )
        except GenerationError as ge:
            await processing_msg.delete()
            await msg.answer(to_user_message(ge.code))
            return
        except Exception:
            await processing_msg.delete()
            logger.exception("T2V start_generation failed")
            await msg.answer("❌ Ошибка генерации видео: попробуйте переделать промт")
            return

        try:
            await processing_msg.delete()
        except Exception:
            pass

        user_after = await get_or_create_user(session, msg.from_user.id)
        balance_left = getattr(user_after, "credits", max(bal_before - settings.COST_CREDITS_QUALITY, 0))

        await state.clear()
        # await msg.answer(await t(session, msg.from_user.id, "task.created", id=task_id))
        await msg.answer(
            "🎬 Видео начало создаваться. Это займёт несколько минут.\n"
            f"💰 Остаток генераций: {balance_left}\n\n"
            "Я пришлю видео сюда, когда оно будет готово!"
        )
