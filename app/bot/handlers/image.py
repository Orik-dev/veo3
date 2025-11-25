from __future__ import annotations

import base64
import aiohttp
from aiogram import Router, F, Dispatcher
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from app.bot.handlers.start import on_start, on_menu_cmd, on_create_video
from app.core.db import SessionLocal
from app.core.logger import logger
from app.core.settings import settings

from app.bot.i18n import t, _load_locales, get_user_lang
from app.bot.keyboards.common import kb_vertical_toggle
from app.bot.init import bot
from app.utils.msg import edit_or_send
from app.utils.tg import safe_cb_answer

from app.domain.generation.service_start import start_generation
from app.domain.users.service import get_or_create_user
from app.domain.generation.error import GenerationError, to_user_message

router = Router(name=__name__)

def register_image_handlers(dp: Dispatcher) -> None:
    dp.include_router(router)

async def _session() -> AsyncSession:
    return SessionLocal()

class I2V(StatesGroup):
    waiting_photo = State()        # ждём фото (с промтом или без)
    waiting_prompt = State()       # ждём промт после фото

async def _strings(session: AsyncSession, user_id: int) -> dict[str, str]:
    lang = await get_user_lang(session, user_id)
    return _load_locales()[lang]

async def _tg_file_to_base64(tg_file_path: str) -> str:
    url = f"https://api.telegram.org/file/bot{bot.token}/{tg_file_path}"
    async with aiohttp.ClientSession() as s:
        async with s.get(url) as r:
            r.raise_for_status()
            raw = await r.read()
            return base64.b64encode(raw).decode("ascii")

# === Обработка команд в любом состоянии ===
@router.message(I2V.waiting_photo, F.text.regexp(r"^/start(?:@.+)?$"))
@router.message(I2V.waiting_prompt, F.text.regexp(r"^/start(?:@.+)?$"))
async def _cmd_start_in_i2v(msg: Message, state: FSMContext):
    await state.clear()
    await on_start(msg)

@router.message(I2V.waiting_photo, F.text.regexp(r"^/(?:menu|create_video)(?:@.+)?$"))
@router.message(I2V.waiting_prompt, F.text.regexp(r"^/(?:menu|create_video)(?:@.+)?$"))
async def _cmd_other_in_i2v(msg: Message, state: FSMContext):
    await state.clear()
    if msg.text.startswith("/menu"):
        await on_menu_cmd(msg)
    else:
        await on_create_video(msg)

# === Вход в режим I2V ===
@router.callback_query(F.data == "menu:image")
async def menu_image(cb: CallbackQuery, state: FSMContext):
    async with SessionLocal() as session:
        await get_or_create_user(session, cb.from_user.id)
        await state.clear()

        # Ранняя проверка баланса
        user = await get_or_create_user(session, cb.from_user.id)
        bal = user.credits
        needed = settings.COST_CREDITS_QUALITY
        if bal < needed:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 Купить генерации", callback_data="menu:packages")],
            ])
            await edit_or_send(
                cb,
                "❌ У вас недостаточно генераций(",
                reply_markup=kb,
            )
            await safe_cb_answer(cb)
            return

        # По умолчанию 9:16
        await state.update_data(ar="9:16", model="veo-3-fast")
        txt = (
            "📸 Отправьте изображение:\n\n"
            # "• С подписью — сразу запущу генерацию\n"
            # "• Без подписи — спрошу описание"
        )
        await edit_or_send(cb, txt, reply_markup=kb_vertical_toggle(is_vertical=True))
        await state.set_state(I2V.waiting_photo)
        await safe_cb_answer(cb)

# === Переключатель AR ===
@router.callback_query(I2V.waiting_photo, F.data == "toggle:ar")
async def toggle_ar(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    ar = data.get("ar", "9:16")
    new_ar = "16:9" if ar == "9:16" else "9:16"
    await state.update_data(ar=new_ar)
    is_vertical = (new_ar == "9:16")
    txt = (
        "📸 Отправьте изображение:\n\n"
        # "• С подписью — сразу запущу генерацию\n"
        # "• Без подписи — спрошу описание"
    )
    await edit_or_send(cb, txt, reply_markup=kb_vertical_toggle(is_vertical=is_vertical))
    await safe_cb_answer(cb)

# === ГЛАВНАЯ ЛОГИКА: Получили фото ===
@router.message(I2V.waiting_photo, F.photo)
async def got_photo(msg: Message, state: FSMContext):
    """
    Два сценария:
    1. Фото + подпись → сразу генерация
    2. Фото без подписи → просим промт
    """
    caption = (msg.caption or "").strip()
    
    # Получаем настройки
    data = await state.get_data()
    model = data.get("model")
    ar = data.get("ar", "9:16")
    
    if not model:
        await msg.answer("❌ Ошибка: не выбрана модель генерации")
        return

    # Загружаем и проверяем фото
    ph = msg.photo[-1]
    f = await bot.get_file(ph.file_id)
    tg_file_path = f.file_path

    try:
        b64 = await _tg_file_to_base64(tg_file_path)
        raw_bytes = len(base64.b64decode(b64))
        if raw_bytes > 20 * 1024 * 1024:
            await msg.answer("❌ Размер изображения превышает 20 МБ.")
            return
    except Exception:
        logger.exception("Failed to fetch telegram image")
        await msg.answer("❌ Не удалось загрузить изображение. Попробуйте ещё раз.")
        return

    # === СЦЕНАРИЙ 1: Фото С подписью → сразу генерация ===
    if caption:
        # Валидация промта
        if len(caption) > 2000:
            await msg.answer("❌ Описание слишком длинное. Максимум 2000 символов.")
            return
        if len(caption) < 5:
            await msg.answer("❌ Описание слишком короткое. Минимум 5 символов.")
            return
        
        # Запуск генерации
        await _start_generation(msg, state, caption, b64, model, ar)
    
    # === СЦЕНАРИЙ 2: Фото БЕЗ подписи → просим промт ===
    else:
        # Сохраняем base64 в state
        await state.update_data(image_b64=b64)
        await state.set_state(I2V.waiting_prompt)
        
        await msg.answer(
            "✅ Изображение получено!\n\n"
            "📝 Теперь отправьте описание (промт):\n"
            "Что должно происходить в видео?"
        )

# === Получили промт ПОСЛЕ фото ===
@router.message(I2V.waiting_prompt, F.text, ~F.text.regexp(r"^/"))
async def got_prompt_after_photo(msg: Message, state: FSMContext):
    """
    Пользователь отправил фото → мы попросили промт → он прислал промт
    """
    prompt = (msg.text or "").strip()
    
    # Валидация промта
    if len(prompt) > 2000:
        await msg.answer("❌ Описание слишком длинное. Максимум 2000 символов.")
        return
    if len(prompt) < 5:
        await msg.answer("❌ Описание слишком короткое. Минимум 5 символов.")
        return
    
    # Достаём сохранённые данные
    data = await state.get_data()
    image_b64 = data.get("image_b64")
    model = data.get("model")
    ar = data.get("ar", "9:16")
    
    if not image_b64:
        await msg.answer("❌ Изображение потеряно. Начните заново: /create_video")
        await state.clear()
        return
    
    # Запуск генерации
    await _start_generation(msg, state, prompt, image_b64, model, ar)

# === Вспомогательная функция запуска генерации ===
async def _start_generation(msg: Message, state: FSMContext, prompt: str, 
                            image_b64: str, model: str, ar: str):
    """
    Единая функция для запуска генерации (из обоих сценариев)
    """
    async with SessionLocal() as session:
        user = await get_or_create_user(session, msg.from_user.id)
        bal_before = user.credits

        processing_msg = await msg.answer("🔄 Отправляем запрос на генерацию…")
        
        try:
            task_id = await start_generation(
                session=session,
                telegram_id=msg.from_user.id,
                prompt=prompt,
                model=model,
                aspect_ratio=ar,
                bytes_image_b64=image_b64,
            )
        except GenerationError as ge:
            await processing_msg.delete()
            await msg.answer(to_user_message(ge.code))
            return
        except Exception:
            await processing_msg.delete()
            logger.exception("I2V start_generation failed")
            await msg.answer("❌ Ошибка генерации видео: попробуйте переделать промт")
            return

        try:
            await processing_msg.delete()
        except Exception:
            pass

        # Остаток генераций
        user_after = await get_or_create_user(session, msg.from_user.id)
        balance_left = getattr(user_after, "credits", max(bal_before - settings.COST_CREDITS_QUALITY, 0))

        await state.clear()
        await msg.answer(
            "🎬 Видео начало создаваться. Это займёт несколько минут.\n"
            f"💰 Остаток генераций: {balance_left}\n\n"
            "Я пришлю видео сюда, когда оно будет готово!"
        )

# === Запреты на другие типы контента ===
@router.message(I2V.waiting_photo, F.document)
async def reject_document_in_i2v(msg: Message, state: FSMContext):
    await msg.answer("❌ Нельзя прикреплять файлы. Отправьте изображение как фото.")

@router.message(I2V.waiting_photo, F.video)
async def reject_video_in_i2v(msg: Message, state: FSMContext):
    await msg.answer("❌ Нельзя прикрепить видео. Отправьте изображение.")

@router.message(I2V.waiting_photo, F.text, ~F.text.regexp(r"^/"))
async def only_text_in_waiting_photo(msg: Message, state: FSMContext):
    await msg.answer("❌ Отправьте изображение (фото), а не текст.")

# === Запреты в состоянии ожидания промта ===
@router.message(I2V.waiting_prompt, F.photo)
async def photo_in_waiting_prompt(msg: Message, state: FSMContext):
    await msg.answer("❌ Я жду описание (текст), а не новое фото.\n\nНапишите, что должно происходить в видео.")

@router.message(I2V.waiting_prompt, F.document)
@router.message(I2V.waiting_prompt, F.video)
async def reject_media_in_waiting_prompt(msg: Message, state: FSMContext):
    await msg.answer("❌ Я жду описание (текст).\n\nНапишите, что должно происходить в видео.")