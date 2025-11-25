from aiogram import Router,Dispatcher
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

router = Router()


def register_bots_handlers(dp: Dispatcher) -> None:
    dp.include_router(router)

@router.message(Command("bots"))
async def show_other_bots(m: Message, state: FSMContext):
    await state.clear()
    text = (
        "🔗 <b>Ознакомьтесь с нашими другими полезными ботами:</b>\n\n"
        
        "🎥 <b>Sora 2 · Создать видео</b> — создавайте супер реалистичные, захватывающие 10 секундные видео с озвучкой в нейросети от создателей ChatGPT.\n"
        "👉 <a href='https://t.me/sora_ai_ibot'>@sora_ai_ibot</a>\n\n"

        "🖌️ <b>Nano Banana · Фотошоп AI</b> — редактирование фото прямо в Telegram.\n"
        "👉 <a href='https://t.me/nano_banana_ibot'>@nano_banana_ibot</a>\n\n"

        "🤖 <b>DeepSeek</b> — мощная китайская нейросеть. Официальный API. Есть голос.\n"
        "👉 <a href='https://t.me/DeepSeek_telegram_bot'>@DeepSeek_telegram_bot</a>\n\n"

        "🍔 <b>КБЖУ по фото</b> — считает калории по фото или голосовому.\n"
        "👉 <a href='https://t.me/calories_by_photo_bot'>@calories_by_photo_bot</a>\n\n"

        "🖼 <b>Реалистичное оживление фото</b> — оживляет статичные фотографии, превращая их в видео.\n"
        "👉 <a href='https://t.me/Ozhivlenie_foto_bot'>@Ozhivlenie_foto_bot</a>\n\n"

        "✨ <b>Seedream 4.0 · Редактирование и создание фото</b> — китайская нейросеть для редактирования и создания фотографий.\n"
        "👉 <a href='https://t.me/seedream_ibot'>@seedream_ibot</a>"
    )
    await m.answer(text, parse_mode="HTML", disable_web_page_preview=True)
