# #app/bot/keyboards/сommon.py
# from aiogram.types import (
#     InlineKeyboardMarkup, InlineKeyboardButton,
#     ReplyKeyboardMarkup, KeyboardButton
# )

# def kb_language() -> InlineKeyboardMarkup:
#     return InlineKeyboardMarkup(inline_keyboard=[[
#         InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
#         InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
#     ]])

# def kb_main(strings: dict[str, str]) -> InlineKeyboardMarkup:
#     """
#     Главная inline‑клава. ВАЖНО: если ссылки нет – ставим callback_data,
#     чтобы не было кнопок без типа.
#     """
#     rows = []

#     # 1) Создать видео
#     rows.append([InlineKeyboardButton(
#         text=strings.get("menu.generate", "🎬 Создать видео"),
#         callback_data="menu:generate"
#     )])

#     # # 2) Примеры генераций (url или callback)
#     # ex_url = strings.get("menu.examples.url")
#     # rows.append([InlineKeyboardButton(
#     #     text=strings.get("menu.examples", "🖌️ Примеры генераций"),
#     #     url=ex_url
#     # )] if ex_url else [InlineKeyboardButton(
#     #     text=strings.get("menu.examples", "🖌️ Примеры генераций"),
#     #     callback_data="menu:examples"
#     # )])

#     # 3) Купить генерации
#     # rows.append([InlineKeyboardButton(
#     #     text=strings.get("menu.packages", "🛒 Купить генерации"),
#     #     callback_data="menu:packages"
#     # )])

#     # # 4) Инструкция (url или callback)
#     # guide_url = strings.get("menu.guide.url")
#     # rows.append([InlineKeyboardButton(
#     #     text=strings.get("menu.guide", "📘 Инструкция"),
#     #     url=guide_url
#     # )] if guide_url else [InlineKeyboardButton(
#     #     text=strings.get("menu.guide", "📘 Инструкция"),
#     #     callback_data="menu:guide"
#     # )])

#     # # 5) Поддержка (url или callback)
#     # sup_url = strings.get("menu.support.url")
#     # rows.append([InlineKeyboardButton(
#     #     text=strings.get("menu.support", "🛟 Чат с поддержкой"),
#     #     url=sup_url
#     # )] if sup_url else [InlineKeyboardButton(
#     #     text=strings.get("menu.support", "🛟 Чат с поддержкой"),
#     #     callback_data="menu:support"
#     # )])

#     return InlineKeyboardMarkup(inline_keyboard=rows)

# def kb_reply_menu(strings: dict[str, str]) -> ReplyKeyboardMarkup:

#     return ReplyKeyboardMarkup(
#         keyboard=[[KeyboardButton(text=strings.get("menu.root_button", "✨ Меню"))]],
#         resize_keyboard=True,
#         one_time_keyboard=False,
#         is_persistent=True,
#         input_field_placeholder=strings.get("menu.input_placeholder", "Write a message...")
#     )

# def kb_ar(strings: dict[str, str]) -> InlineKeyboardMarkup:
#     return InlineKeyboardMarkup(inline_keyboard=[
#         [InlineKeyboardButton(text="9:16 — вертикальное (Reels/Shorts)", callback_data="ar:9x16")],
#         [InlineKeyboardButton(text="16:9 — горизонтальное (YouTube)", callback_data="ar:16x9")],
#         # [InlineKeyboardButton(text="1:1", callback_data="ar:1x1")],
#     ])

# def kb_model(strings: dict[str, str]) -> InlineKeyboardMarkup:
#     return InlineKeyboardMarkup(inline_keyboard=[
#         [InlineKeyboardButton(text=strings["mode.fast.short"], callback_data="model:veo3_fast")],
#         [InlineKeyboardButton(text=strings["mode.quality.short"], callback_data="model:veo3")],
#     ])

# def kb_model_short(strings: dict[str, str]) -> InlineKeyboardMarkup:
#     return InlineKeyboardMarkup(inline_keyboard=[
#         [InlineKeyboardButton(text=strings["mode.fast.short"],     callback_data="model:veo3_fast")],
#         [InlineKeyboardButton(text=strings["mode.quality.short"],  callback_data="model:veo3")],
#         [InlineKeyboardButton(text=strings["btn.back"],            callback_data="menu:root")]
#     ])

# def kb_confirm_text(strings: dict[str, str]) -> InlineKeyboardMarkup:
#     return InlineKeyboardMarkup(inline_keyboard=[
#         [InlineKeyboardButton(text=strings["btn.confirm"],      callback_data="confirm:start")],
#         [InlineKeyboardButton(text=strings["btn.edit_prompt"], callback_data="edit:prompt")],
#         # [InlineKeyboardButton(text=strings["btn.edit_options"], callback_data="edit:options")],
#         [InlineKeyboardButton(text=strings["btn.back"],         callback_data="menu:root")],
#     ])

# def kb_confirm_image(strings: dict[str, str]) -> InlineKeyboardMarkup:
#     return InlineKeyboardMarkup(inline_keyboard=[
#         [InlineKeyboardButton(text=strings["btn.confirm"],   callback_data="confirm:start")],
#         [InlineKeyboardButton(text=strings["btn.edit_prompt"],    callback_data="edit:prompt")],
#         [InlineKeyboardButton(text=strings["btn.change_image"],   callback_data="edit:image")],
#         # [InlineKeyboardButton(text=strings["btn.edit_options"],   callback_data="edit:options")],
#         [InlineKeyboardButton(text=strings["menu.root_button"],           callback_data="menu:root")],
#     ])

# def kb_generate_type(strings: dict[str, str]) -> InlineKeyboardMarkup:
#     return InlineKeyboardMarkup(inline_keyboard=[
#         [InlineKeyboardButton(text=strings.get("gen.from_image", "📸 Сгенерировать видео по фото"), callback_data="menu:image")],
#         [InlineKeyboardButton(text=strings.get("gen.from_text", "📝 Сгенерировать видео по тексту"), callback_data="menu:text")],
#         # [InlineKeyboardButton(text=strings.get("btn.back", "↩️ Назад"), callback_data="menu:root")],
#     ])



# def kb_packages(packages: dict[int, int]) -> InlineKeyboardMarkup:
#     rows = []
#     for qty, price in sorted(packages.items()):
#         rows.append([InlineKeyboardButton(
#             text=f"{qty} генераций — {price} ₽",
#             callback_data=f"pay:pkg:{qty}"
#         )])
#     rows.append([InlineKeyboardButton(text="↩️ Назад", callback_data="menu:root")])
#     return InlineKeyboardMarkup(inline_keyboard=rows)
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)

def kb_language() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
    ]])

def kb_main(strings: dict[str, str]) -> InlineKeyboardMarkup:
    rows = []
    rows.append([InlineKeyboardButton(
        text=strings.get("menu.generate", "🎬 Создать видео"),
        callback_data="menu:generate"
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_reply_menu(strings: dict[str, str]) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=strings.get("menu.root_button", "✨ Меню"))]],
        resize_keyboard=True,
        one_time_keyboard=False,
        is_persistent=True,
        input_field_placeholder=strings.get("menu.input_placeholder", "Write a message...")
    )

# ── ТУМБЛЕР для I2V (оставляем — он нужен для режима «по фото»)
def kb_vertical_toggle(is_vertical: bool) -> InlineKeyboardMarkup:
    label = "Вертикальное видео ✅" if is_vertical else "Вертикальное видео "
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label, callback_data="toggle:ar")],
        # [InlineKeyboardButton(text="↩️ Назад", callback_data="menu:root")]
    ])

# ── ВОЗВРАЩЁННАЯ КЛАВА: выбор формата для T2V (текстовый режим)
def kb_ar(strings: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="9:16 — вертикальное (Reels/Shorts)", callback_data="ar:9x16")],
        [InlineKeyboardButton(text="16:9 — горизонтальное (YouTube)",   callback_data="ar:16x9")],
    ])

def kb_model(strings: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=strings["mode.fast.short"], callback_data="model:veo3_fast")],
        [InlineKeyboardButton(text=strings["mode.quality.short"], callback_data="model:veo3")],
    ])

def kb_model_short(strings: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=strings["mode.fast.short"],     callback_data="model:veo3_fast")],
        [InlineKeyboardButton(text=strings["mode.quality.short"],  callback_data="model:veo3")],
        [InlineKeyboardButton(text=strings["btn.back"],            callback_data="menu:root")]
    ])

def kb_confirm_text(strings: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=strings["btn.confirm"],      callback_data="confirm:start")],
        [InlineKeyboardButton(text=strings["btn.edit_prompt"],  callback_data="edit:prompt")],
        [InlineKeyboardButton(text=strings["btn.back"],         callback_data="menu:root")],
    ])

def kb_confirm_image(strings: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=strings["btn.confirm"],      callback_data="confirm:start")],
        [InlineKeyboardButton(text=strings["btn.edit_prompt"],  callback_data="edit:prompt")],
        [InlineKeyboardButton(text=strings["btn.change_image"], callback_data="edit:image")],
        [InlineKeyboardButton(text=strings["menu.root_button"], callback_data="menu:root")],
    ])

def kb_generate_type(strings: dict[str, str]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=strings.get("gen.from_image", "📸 Сгенерировать видео по фото"), callback_data="menu:image")],
        [InlineKeyboardButton(text=strings.get("gen.from_text",  "📝 Сгенерировать видео по тексту"), callback_data="menu:text")],
    ])

def kb_packages(packages: dict[int, int]) -> InlineKeyboardMarkup:
    rows = []
    for qty, price in sorted(packages.items()):
        rows.append([InlineKeyboardButton(
            text=f"{qty} генераций — {price} ₽",
            callback_data=f"pay:pkg:{qty}"
        )])
    rows.append([InlineKeyboardButton(text="↩️ Назад", callback_data="menu:root")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
