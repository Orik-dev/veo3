# app/bot/handlers/start.py
from __future__ import annotations

from aiogram import Router, F, Dispatcher
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
# from app.bot.handlers.invite import apply_referral_on_start
from app.core.db import SessionLocal
from app.domain.users.service import upsert_from_message, set_locale
from app.bot.i18n import t, _load_locales, get_user_lang
from app.bot.keyboards.common import kb_language, kb_main, kb_generate_type, kb_reply_menu
from app.utils.msg import edit_or_send
from app.utils.tg import safe_cb_answer
from app.domain.users.service import get_or_create_user, get_balance
from aiogram.types import ReplyKeyboardRemove

from sqlalchemy import update
from app.models.models import User

router = Router(name=__name__)

# Невидимый символ: не отображается в чате, но удовлетворяет Telegram (нельзя слать пустой текст)
_ZWJ = "\u2060"  # ZERO WIDTH JOINER


def _norm(s: str) -> str:
    return (s or "").strip().casefold()


def _is_menu_text(txt: str, label: str) -> bool:
    # label — текст кнопки из i18n; добавим алиасы на всякий случай
    return _norm(txt) in {_norm(label), "меню", "menu"}


def register_start_handlers(dp: Dispatcher) -> None:
    dp.include_router(router)


# @router.message(CommandStart())
# async def on_start(msg: Message):
#     async with SessionLocal() as session:
#         # await apply_referral_on_start(msg)
#         await upsert_from_message(session, msg)
#         await set_locale(session,msg.from_user.id,"ru")
#         bundles = _load_locales()

#     # Выбор языка (inline)
#     # await msg.answer(bundles["ru"]["lang.choose"], reply_markup=kb_language())
#     # Приклеим reply-кнопку «Меню» без текста (один раз, дальше её не дублируем)
#     # await msg.answer(_ZWJ, reply_markup=kb_reply_menu(bundles["ru"]))


# @router.callback_query(F.data.startswith("lang:"))
# async def on_set_lang(cb: CallbackQuery):
#     lang = cb.data.split(":")[1]
#     async with SessionLocal() as session:
#         await set_locale(session, cb.from_user.id, lang)
#         bundles = _load_locales()
#         strings = bundles["ru"] if lang == "ru" else bundles["en"]

#     # Текст для подписи к фото
   
#     title = strings.get("menu.title", "Главное меню" if lang == "ru" else "Main menu")

#     # if lang == "ru":
#     #     extra = (
#     #     "👋 Добро пожаловать!\n"
#     #     "Это бот для генерации уникальных видео со звуком с помощью нейросети Veo3.\n\n"
#     #     "✨ Просто отправьте описание (промт) того, какое видео вы хотите создать.\n"
#     #     "📸 Можно прикрепить фото — тогда видео будет сгенерировано с учётом изображения.\n\n"
#     #     "🪙 Оплатить генерацию можно как в рублях, так и в звёздочках!\n\n"
#     #     "💸 У нас самые дешёвые цены на рынке!\n\n"
#     #     "Нажмите меню или кнопку ниже чтобы создать видео\n\n"
#     #      'Пользуясь ботом, Вы принимаете наше <a href="https://example.com">пользовательское соглашение</a> и <a href="https://telegram.org/privacy-tpa">политику конфиденциальности</a>.',
#     # )
#     # else:
#     #     extra = (
#     #         "👋 Welcome!\n"
#     #         "This bot generates unique videos with sound using the Veo3 model.\n\n"
#     #         "✨ Just send a description (prompt) of the video you want to create.\n"
#     #         "📸 You can attach a photo — the video will be generated based on the image.\n\n"
#     #         "🪙 Payment can be made in rubles or stars!\n\n"
#     #         "💸 We offer the cheapest prices on the market!\n\n"
#     #         "Click the menu or the button below to create a video\n\n"
#     #         'By using this bot, you agree to our <a href="https://example.com">User Agreement</a> and <a href="https://example.com/privacy-policy">Privacy Policy</a>.'
#     #     )
#     if lang == "ru":
#         extra = (
#             "👋 Добро пожаловать!\n"
#             "Это бот для генерации уникальных видео со звуком с помощью нейросети Veo3.\n\n"
#             "✨ Просто отправьте описание (промт) того, какое видео вы хотите создать.\n"
#             "📸 Можно прикрепить фото — тогда видео будет сгенерировано с учётом изображения.\n\n"
#             "🪙 Оплатить генерацию можно как в рублях, так и в звёздочках!\n\n"
#             "💸 У нас самые дешёвые цены на рынке!\n\n"
#             "Нажмите меню или кнопку ниже чтобы создать видео.\n\n"
#             'Пользуясь ботом, Вы принимаете наше <a href="https://docs.google.com/document/d/1-gydz41g4rkTuvAKS3oHHOa4xZ_dcvPjtxLluo2OMxY/edit?tab=t.0">пользовательское соглашение</a> и <a href="https://telegram.org/privacy-tpa">политику конфиденциальности</a>.'
#         )
#     else:
#         extra = (
#             "👋 Welcome!\n"
#             "This bot generates unique videos with sound using the Veo3 model.\n\n"
#             "✨ Just send a description (prompt) of the video you want to create.\n"
#             "📸 You can attach a photo — the video will be generated based on the image.\n\n"
#             "🪙 Payment can be made in rubles or stars!\n\n"
#             "💸 We offer the cheapest prices on the market!\n\n"
#             "Click the menu or the button below to create a video.\n\n"
#             'By using this bot, you agree to our <a href="https://example.com/user-agreement">User Agreement</a> and <a href="https://example.com/privacy-policy">Privacy Policy</a>.'
#         )

#     caption = f"{extra}"
#     # ОДНО сообщение: фото + подпись + инлайн-меню
#     sent = False
#     try:
#         from app.core.settings import settings
#         from aiogram.types import FSInputFile

#         if getattr(settings, "GREETING_IMAGE_PATH", None):
#             file = FSInputFile(settings.GREETING_IMAGE_PATH)
#             await cb.message.answer_photo(photo=file, caption=caption, reply_markup=kb_main(strings),disable_web_page_preview=True)
#             sent = True
#         elif getattr(settings, "GREETING_IMAGE_URL", None):
#             await cb.message.answer_photo(photo=settings.GREETING_IMAGE_URL, caption=caption, reply_markup=kb_main(strings),disable_web_page_preview=True)
#             sent = True
#     except Exception:
#         # пропускаем — ниже сделаем текстовый фолбэк
#         pass

#     # Фолбэк: если не удалось отправить фото — отправим текст + меню
#     if not sent:
#         await edit_or_send(cb, caption, reply_markup=kb_main(strings))

#     await safe_cb_answer(cb)

@router.message(CommandStart())
async def on_start(msg: Message):
    async with SessionLocal() as session:
        # await apply_referral_on_start(msg)
        await upsert_from_message(session, msg)
        
        # Устанавливаем русский язык по умолчанию
        await set_locale(session, msg.from_user.id, "ru")
        
        bundles = _load_locales()
        strings = bundles["ru"]

    # ЗАКОММЕНТИРОВАНО: Выбор языка (inline)
    # await msg.answer(bundles["ru"]["lang.choose"], reply_markup=kb_language())
    
    # Сразу показываем главное меню на русском языке
    extra = (
        "👋 Добро пожаловать!\n"
        "Это бот для генерации уникальных видео со звуком с помощью нейросети Veo3.\n\n"
        "✨ Просто отправьте описание (промт) того, какое видео вы хотите создать.\n"
        "📸 Можно прикрепить фото — тогда видео будет сгенерировано с учётом изображения.\n\n"
        "🪙 Оплатить генерацию можно как в рублях, так и в звёздочках!\n\n"
        "💸 У нас самые дешёвые цены на рынке!\n\n"
        "Нажмите меню или кнопку ниже чтобы создать видео.\n\n"
        'Пользуясь ботом, Вы принимаете наше <a href="https://docs.google.com/document/d/1-gydz41g4rkTuvAKS3oHHOa4xZ_dcvPjtxLluo2OMxY/edit?tab=t.0">пользовательское соглашение</a> и <a href="https://telegram.org/privacy-tpa">политику конфиденциальности</a>.'
    )
    
    caption = f"{extra}"
    
    # Отправка приветственного сообщения
    sent = False
    try:
        from app.core.settings import settings
        from aiogram.types import FSInputFile

        if getattr(settings, "GREETING_IMAGE_PATH", None):
            file = FSInputFile(settings.GREETING_IMAGE_PATH)
            await msg.answer_photo(photo=file, caption=caption, reply_markup=kb_main(strings), disable_web_page_preview=True)
            sent = True
        elif getattr(settings, "GREETING_IMAGE_URL", None):
            await msg.answer_photo(photo=settings.GREETING_IMAGE_URL, caption=caption, reply_markup=kb_main(strings), disable_web_page_preview=True)
            sent = True
    except Exception:
        pass

    # Фолбэк: если не удалось отправить фото — отправим текст + меню
    if not sent:
        await msg.answer(caption, reply_markup=kb_main(strings))
@router.callback_query(F.data == "menu:generate")
async def on_menu_generate(cb: CallbackQuery):
    async with SessionLocal() as session:
        bundles = _load_locales()
        try:
            lang = await get_user_lang(session, cb.from_user.id)
        except Exception:
            lang = "ru"
        strings = bundles["ru"] if lang == "ru" else bundles["en"]
        
        user = await get_or_create_user(session, cb.from_user.id)

        # подстраховка: если в БД нет username, но в TG он есть — обновим
        try:
            if hasattr(User, "username"):
                tg_username = cb.from_user.username or None
                if tg_username and tg_username != getattr(user, "username", None):
                    await session.execute(
                        update(User)
                        .where(User.user_id == cb.from_user.id)
                        .values(username=tg_username)
                    )
                    await session.commit()
                    user.username = tg_username
        except Exception:
            pass
        bal = await get_balance(session, cb.from_user.id)
        name = (
            getattr(user, "username", None)
            or cb.from_user.username
            or cb.from_user.full_name
            or cb.from_user.first_name
            or ("друг" if lang == "ru" else "friend")
        )
        txt = (
            f"👋 Привет, {name}!\n"
            f"💰 Ваш баланс: <b>{bal}</b> генераций\n\n"
            "🎬 𝗚𝗼𝗼𝗴𝗹𝗲 𝗩𝗘𝗢 𝟯.𝟭 — нейросеть для генерации видео (8 секунд) со звуком.\n"
        )

    await cb.message.answer(txt, reply_markup=kb_generate_type(strings), parse_mode="HTML")
    await safe_cb_answer(cb)


@router.callback_query(F.data == "menu:root")
async def on_menu_root(cb: CallbackQuery):
    async with SessionLocal() as session:
        bundles = _load_locales()
        try:
            lang = await get_user_lang(session, cb.from_user.id)
        except Exception:
            lang = "ru"

        strings = {**(bundles["ru"] if lang == "ru" else bundles["en"])}

        from app.core.settings import settings
        if settings.EXAMPLES_URL:
            strings["menu.examples.url"] = settings.EXAMPLES_URL
        if settings.GUIDE_URL:
            strings["menu.guide.url"] = settings.GUIDE_URL
        if settings.SUPPORT_URL:
            strings["menu.support.url"] = settings.SUPPORT_URL

        title = await t(session, cb.from_user.id, "menu.title")

    await edit_or_send(cb, title, reply_markup=kb_main(strings))
    await safe_cb_answer(cb)


@router.message(Command("create_video"))
async def on_create_video(msg: Message):
    async with SessionLocal() as session:
        bundles = _load_locales()
        try:
            lang = await get_user_lang(session, msg.from_user.id)
        except Exception:
            lang = "ru"
        strings = bundles["ru"] if lang == "ru" else bundles["en"]

        # гарантируем пользователя
        user = await get_or_create_user(session, msg.from_user.id)

        # обновим username из TG, если в БД пусто/другое
        try:
            if hasattr(User, "username"):
                tg_username = msg.from_user.username or None
                if tg_username and tg_username != getattr(user, "username", None):
                    await session.execute(
                        update(User)
                        .where(User.user_id == msg.from_user.id)
                        .values(username=tg_username)
                    )
                    await session.commit()
                    user.username = tg_username
        except Exception:
            pass

        bal = await get_balance(session, msg.from_user.id)
        # name = (
        #     getattr(user, "username", None)
        #     or msg.from_user.username
        #     or msg.from_user.full_name
        #     or msg.from_user.first_name
        #     or ("друг" if lang == "ru" else "friend")
        # )
        # choose = strings.get(
        #     "gen.choose_source",
        #     "Выберите источник генерации" if lang == "ru" else "Choose a source"
        # )

        if lang == "ru":
            txt = (
                # f"👋 Привет, {name}!\n"
                f"💰 Ваш баланс: <b>{bal}</b> генераций\n\n"
                "🎬 𝗚𝗼𝗼𝗴𝗹𝗲 𝗩𝗘𝗢 𝟯 — нейросеть для генерации видео (8 секунд) со звуком.\n\n"
                # f"{choose}"
            )
        else:
            txt = (
                # f"👋 Hi, {name}!\n"
                f"💰 Your balance: <b>{bal}</b> generations\n\n"
                "🎬 Google VEO 3 generates 8-second videos with sound.\n\n"
                # f"{choose}"
            )

    # если у бота не задан parse_mode глобально — добавь parse_mode="HTML"
    await msg.answer(txt, reply_markup=kb_generate_type(strings), parse_mode="HTML")



@router.message(Command("menu"))
async def on_menu_cmd(msg: Message):
    async with SessionLocal() as session:
        bundles = _load_locales()
        try:
            lang = await get_user_lang(session, msg.from_user.id)
        except Exception:
            lang = "ru"

        strings = {**(bundles["ru"] if lang == "ru" else bundles["en"])}

        from app.core.settings import settings
        if settings.EXAMPLES_URL:
            strings["menu.examples.url"] = settings.EXAMPLES_URL
        if settings.GUIDE_URL:
            strings["menu.guide.url"] = settings.GUIDE_URL
        if settings.SUPPORT_URL:
            strings["menu.support.url"] = settings.SUPPORT_URL

        title = await t(session, msg.from_user.id, "menu.title")

    await msg.answer(title, reply_markup=kb_main(strings))
    # Без дублирования reply-клавы/подсказок



@router.message(Command("help"))
async def on_help_cmd(msg: Message):
    async with SessionLocal() as session:
        bundles = _load_locales()
        try:
            lang = await get_user_lang(session, msg.from_user.id)
        except Exception:
            lang = "ru"
        strings = bundles["ru"] if lang == "ru" else bundles["en"]

    text = f"{strings['menu.guide']}\n{strings['menu.support']}"
    await msg.answer(text, reply_markup=kb_main(strings))


# === ДОБАВИТЬ В КОНЕЦ ФАЙЛА СО СТАРТОВЫМИ ХЭНДЛЕРАМИ ===
@router.message(F.text.in_({"✨ Меню", "Меню", "menu", "Menu"}))
async def on_reply_menu_text(msg: Message):
    # 1) получаем локаль и строки
    async with SessionLocal() as session:
        try:
            lang = await get_user_lang(session, msg.from_user.id)
        except Exception:
            lang = "ru"

        bundles = _load_locales()
        strings = {**(bundles["ru"] if lang == "ru" else bundles["en"])}

        # текст нашей reply-кнопки из i18n (как в kb_reply_menu)
        reply_label = strings.get("reply.menu.text", "✨ Меню")

        # если это не нажатие нашей кнопки — выходим, пусть ловят другие хэндлеры
        if not _is_menu_text(msg.text, reply_label):
            return

        # подтянем внешние ссылки, как в on_menu_root
        from app.core.settings import settings
        if settings.EXAMPLES_URL:
            strings["menu.examples.url"] = settings.EXAMPLES_URL
        if settings.GUIDE_URL:
            strings["menu.guide.url"] = settings.GUIDE_URL
        if settings.SUPPORT_URL:
            strings["menu.support.url"] = settings.SUPPORT_URL

        title = await t(session, msg.from_user.id, "menu.title")

    # 2) показываем основное меню (inline)
    await msg.answer(title, reply_markup=kb_main(strings))
# === КОНЕЦ ДОБАВКИ ===
