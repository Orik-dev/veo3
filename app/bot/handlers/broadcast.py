# # from __future__ import annotations
# # import uuid
# # from aiogram import Router, Dispatcher
# # from aiogram.filters import Command
# # from aiogram.types import Message
# # from sqlalchemy import select, update
# # from arq.connections import ArqRedis, RedisSettings, create_pool

# # from app.core.settings import settings
# # from app.core.db import SessionLocal
# # from app.models.models import BroadcastJob, User

# # router = Router(name=__name__)

# # def register_broadcast_handlers(dp: Dispatcher) -> None:
# #     dp.include_router(router)

# # def _is_admin(uid: int) -> bool:
# #     return settings.ADMIN_ID and int(settings.ADMIN_ID) == int(uid)

# # async def _arq() -> ArqRedis:
# #     return await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))

# # @router.message(Command("broadcast"))
# # async def cmd_broadcast(msg: Message):
# #     if not _is_admin(msg.from_user.id):
# #         return
# #     text = (msg.text or "").split(" ", 1)
# #     if len(text) < 2 or not text[1].strip():
# #         await msg.answer("Использование: <code>/broadcast Текст рассылки</code>")
# #         return
# #     payload = text[1].strip()

# #     # создаём Job
# #     job_id = str(uuid.uuid4())
# #     async with SessionLocal() as session:
# #         total = (await session.execute(select(User.user_id))).scalars().unique().all()
# #         bj = BroadcastJob(
# #             id=job_id,
# #             created_by=msg.from_user.id,
# #             text=payload,
# #             status="queued",
# #             total=len(total)
# #         )
# #         session.add(bj)
# #         await session.commit()

# #     # кидаем в ARQ
# #     arq = await _arq()
# #     await arq.enqueue_job("broadcast_send", job_id)

# #     await msg.answer(f"🚀 Запустил рассылку #{job_id}\nВсего пользователей: {bj.total}\nКоманда отмены: /broadcast_cancel {job_id}\nСтатус: /broadcast_status {job_id}")

# # @router.message(Command("broadcast_cancel"))
# # async def cmd_broadcast_cancel(msg: Message):
# #     if not _is_admin(msg.from_user.id):
# #         return
# #     parts = (msg.text or "").split(" ", 1)
# #     if len(parts) < 2:
# #         await msg.answer("Использование: <code>/broadcast_cancel JOB_ID</code>")
# #         return
# #     job_id = parts[1].strip()
# #     async with SessionLocal() as session:
# #         await session.execute(
# #             update(BroadcastJob)
# #             .where(BroadcastJob.id == job_id)
# #             .values(status="cancelled")
# #         )
# #         await session.commit()
# #     await msg.answer(f"⏹ Отменил рассылку #{job_id}")

# # @router.message(Command("broadcast_status"))
# # async def cmd_broadcast_status(msg: Message):
# #     if not _is_admin(msg.from_user.id):
# #         return
# #     parts = (msg.text or "").split(" ", 1)
# #     if len(parts) < 2:
# #         await msg.answer("Использование: <code>/broadcast_status JOB_ID</code>")
# #         return
# #     job_id = parts[1].strip()
# #     async with SessionLocal() as session:
# #         row = await session.execute(select(BroadcastJob).where(BroadcastJob.id == job_id))
# #         bj = row.scalars().first()
# #     if not bj:
# #         await msg.answer("Не нашёл такую рассылку")
# #         return
# #     await msg.answer(f"Рассылка #{bj.id}\nСтатус: {bj.status}\nВсего: {bj.total}\nОтправлено: {bj.sent}\nОшибок: {bj.failed}\n{('Заметка: ' + bj.note) if bj.note else ''}")


# from __future__ import annotations
# import uuid
# from aiogram import Router, Dispatcher, F
# from aiogram.filters import Command
# from aiogram.types import Message
# from sqlalchemy import select, update
# from arq.connections import ArqRedis, RedisSettings, create_pool

# from app.core.settings import settings
# from app.core.db import SessionLocal
# from app.models.models import BroadcastJob, User

# router = Router(name=__name__)

# def register_broadcast_handlers(dp: Dispatcher) -> None:
#     dp.include_router(router)

# def _is_admin(uid: int) -> bool:
#     return settings.ADMIN_ID and int(settings.ADMIN_ID) == int(uid)

# async def _arq() -> ArqRedis:
#     return await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))

# @router.message(Command("broadcast"))
# async def cmd_broadcast(msg: Message):
#     """
#     Поддерживает 3 формата:
#     1. /broadcast Текст — только текстовая рассылка
#     2. Фото + подпись /broadcast Текст — рассылка с фото
#     3. Видео + подпись /broadcast Текст — рассылка с видео
#     """
#     if not _is_admin(msg.from_user.id):
#         return
    
#     # Извлекаем текст (из caption для медиа или из text)
#     raw_text = (msg.caption or msg.text or "").strip()
#     if not raw_text.startswith("/broadcast"):
#         return
    
#     # Убираем команду
#     parts = raw_text.split(maxsplit=1)
#     if len(parts) < 2 or not parts[1].strip():
#         await msg.answer(
#             "📣 <b>Использование:</b>\n\n"
#             "1️⃣ Текстовая рассылка:\n"
#             "<code>/broadcast Ваш текст</code>\n\n"
#             "2️⃣ Рассылка с фото:\n"
#             "Прикрепите фото + подпись:\n"
#             "<code>/broadcast Ваш текст</code>\n\n"
#             "3️⃣ Рассылка с видео:\n"
#             "Прикрепите видео + подпись:\n"
#             "<code>/broadcast Ваш текст</code>",
#             parse_mode="HTML"
#         )
#         return
    
#     payload = parts[1].strip()
    
#     # Определяем тип медиа
#     media_type = None
#     media_file_id = None
    
#     if msg.photo:
#         media_type = "photo"
#         media_file_id = msg.photo[-1].file_id  # берём самое большое фото
#     elif msg.video:
#         media_type = "video"
#         media_file_id = msg.video.file_id
    
#     # Создаём Job
#     job_id = str(uuid.uuid4())
#     async with SessionLocal() as session:
#         total = (await session.execute(select(User.user_id))).scalars().unique().all()
#         bj = BroadcastJob(
#             id=job_id,
#             created_by=msg.from_user.id,
#             text=payload,
#             media_type=media_type,
#             media_file_id=media_file_id,
#             status="queued",
#             total=len(total)
#         )
#         session.add(bj)
#         await session.commit()

#     # Кидаем в ARQ
#     arq = await _arq()
#     await arq.enqueue_job("broadcast_send", job_id)
    
#     media_info = ""
#     if media_type == "photo":
#         media_info = "\n📸 С фотографией"
#     elif media_type == "video":
#         media_info = "\n🎬 С видео"
    
#     await msg.answer(
#         f"🚀 Запустил рассылку <code>#{job_id}</code>{media_info}\n"
#         f"Всего пользователей: <b>{bj.total}</b>\n\n"
#         f"Команда отмены: <code>/broadcast_cancel {job_id}</code>\n"
#         f"Статус: <code>/broadcast_status {job_id}</code>",
#         parse_mode="HTML"
#     )

# @router.message(Command("broadcast_cancel"))
# async def cmd_broadcast_cancel(msg: Message):
#     if not _is_admin(msg.from_user.id):
#         return
#     parts = (msg.text or "").split(" ", 1)
#     if len(parts) < 2:
#         await msg.answer("Использование: <code>/broadcast_cancel JOB_ID</code>", parse_mode="HTML")
#         return
#     job_id = parts[1].strip()
#     async with SessionLocal() as session:
#         await session.execute(
#             update(BroadcastJob)
#             .where(BroadcastJob.id == job_id)
#             .values(status="cancelled")
#         )
#         await session.commit()
#     await msg.answer(f"⏹ Отменил рассылку <code>#{job_id}</code>", parse_mode="HTML")

# @router.message(Command("broadcast_status"))
# async def cmd_broadcast_status(msg: Message):
#     if not _is_admin(msg.from_user.id):
#         return
#     parts = (msg.text or "").split(" ", 1)
#     if len(parts) < 2:
#         await msg.answer("Использование: <code>/broadcast_status JOB_ID</code>", parse_mode="HTML")
#         return
#     job_id = parts[1].strip()
#     async with SessionLocal() as session:
#         row = await session.execute(select(BroadcastJob).where(BroadcastJob.id == job_id))
#         bj = row.scalars().first()
#     if not bj:
#         await msg.answer("❌ Не нашёл такую рассылку")
#         return
    
#     media_info = ""
#     if bj.media_type == "photo":
#         media_info = "\n📸 Тип: фото"
#     elif bj.media_type == "video":
#         media_info = "\n🎬 Тип: видео"
#     else:
#         media_info = "\n📝 Тип: текст"
    
#     await msg.answer(
#         f"📊 Рассылка <code>#{bj.id}</code>\n"
#         f"Статус: <b>{bj.status}</b>{media_info}\n"
#         f"Всего: <b>{bj.total}</b>\n"
#         f"Отправлено: <b>{bj.sent}</b>\n"
#         f"Ошибок: <b>{bj.failed}</b>\n"
#         f"{('Заметка: ' + bj.note) if bj.note else ''}",
#         parse_mode="HTML"
#     )
    
    
# @router.message(Command("broadcast_test"))
# async def cmd_broadcast_test(msg: Message):
#     """
#     Тестовая рассылка — отправляет только админу
#     """
#     if not _is_admin(msg.from_user.id):
#         return
    
#     # Извлекаем текст (из caption для медиа или из text)
#     raw_text = (msg.caption or msg.text or "").strip()
#     if not raw_text.startswith("/broadcast_test"):
#         return
    
#     parts = raw_text.split(maxsplit=1)
#     if len(parts) < 2 or not parts[1].strip():
#         await msg.answer("Использование: <code>/broadcast_test Текст</code>", parse_mode="HTML")
#         return
    
#     payload = parts[1].strip()
    
#     # Определяем тип медиа
#     media_type = None
#     media_file_id = None
    
#     if msg.photo:
#         media_type = "photo"
#         media_file_id = msg.photo[-1].file_id
#     elif msg.video:
#         media_type = "video"
#         media_file_id = msg.video.file_id
    
#     # Отправляем ТОЛЬКО админу
#     try:
#         if media_type == "photo" and media_file_id:
#             await msg.bot.send_photo(
#                 msg.from_user.id, 
#                 photo=media_file_id, 
#                 caption=f"🧪 ТЕСТ РАССЫЛКИ:\n\n{payload}"
#             )
#         elif media_type == "video" and media_file_id:
#             await msg.bot.send_video(
#                 msg.from_user.id, 
#                 video=media_file_id, 
#                 caption=f"🧪 ТЕСТ РАССЫЛКИ:\n\n{payload}"
#             )
#         else:
#             await msg.answer(f"🧪 ТЕСТ РАССЫЛКИ:\n\n{payload}")
        
#         await msg.answer("✅ Тестовое сообщение отправлено вам успешно!")
#     except Exception as e:
#         await msg.answer(f"❌ Ошибка теста: {e}")    

from __future__ import annotations
import uuid
import os
from pathlib import Path
from aiogram import Router, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select, update
from arq.connections import ArqRedis, RedisSettings, create_pool

from app.core.settings import settings
from app.core.db import SessionLocal
from app.core.logger import logger
from app.models.models import BroadcastJob, User

router = Router(name=__name__)

# Создать папку для медиа
MEDIA_DIR = Path("broadcast_media")
MEDIA_DIR.mkdir(exist_ok=True)

def register_broadcast_handlers(dp: Dispatcher) -> None:
    dp.include_router(router)

def _is_admin(uid: int) -> bool:
    return settings.ADMIN_ID and int(settings.ADMIN_ID) == int(uid)

async def _arq() -> ArqRedis:
    return await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))

@router.message(Command("broadcast"))
async def cmd_broadcast(msg: Message):
    """
    Поддерживает 3 формата:
    1. /broadcast Текст — только текстовая рассылка
    2. Фото + подпись /broadcast Текст — рассылка с фото
    3. Видео + подпись /broadcast Текст — рассылка с видео
    """
    if not _is_admin(msg.from_user.id):
        return
    
    # Извлекаем текст (из caption для медиа или из text)
    raw_text = (msg.caption or msg.text or "").strip()
    if not raw_text.startswith("/broadcast"):
        return
    
    # Убираем команду
    parts = raw_text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await msg.answer(
            "📣 <b>Использование:</b>\n\n"
            "1️⃣ Текстовая рассылка:\n"
            "<code>/broadcast Ваш текст</code>\n\n"
            "2️⃣ Рассылка с фото:\n"
            "Прикрепите фото + подпись:\n"
            "<code>/broadcast Ваш текст</code>\n\n"
            "3️⃣ Рассылка с видео:\n"
            "Прикрепите видео + подпись:\n"
            "<code>/broadcast Ваш текст</code>",
            parse_mode="HTML"
        )
        return
    
    payload = parts[1].strip()
    
    media_type = None
    media_file_id = None
    media_file_path = None
    
    # Фото — используем file_id (работает отлично)
    if msg.photo:
        media_type = "photo"
        media_file_id = msg.photo[-1].file_id
    
    # Видео — скачиваем локально
    elif msg.video:
        media_type = "video"
        media_file_id = msg.video.file_id
        
        try:
            # Показываем прогресс
            progress_msg = await msg.answer("⏳ Скачиваю видео для рассылки...")
            
            # Скачиваем файл
            file = await msg.bot.get_file(msg.video.file_id)
            file_path = file.file_path
            
            # Генерируем уникальное имя
            job_id_temp = str(uuid.uuid4())
            ext = Path(file_path).suffix or ".mp4"
            local_path = MEDIA_DIR / f"{job_id_temp}{ext}"
            
            # Скачиваем через Telegram Bot API
            await msg.bot.download_file(file_path, local_path)
            
            media_file_path = str(local_path)
            
            # Получаем размер файла
            file_size_mb = local_path.stat().st_size / 1024 / 1024
            
            await progress_msg.edit_text(f"✅ Видео скачано ({file_size_mb:.1f} МБ), запускаю рассылку...")
            
        except Exception as e:
            await msg.answer(f"❌ Ошибка скачивания видео: {e}")
            logger.exception("Failed to download video for broadcast")
            return
    
    # Создаём Job
    job_id = str(uuid.uuid4())
    async with SessionLocal() as session:
        total = (await session.execute(select(User.user_id))).scalars().unique().all()
        bj = BroadcastJob(
            id=job_id,
            created_by=msg.from_user.id,
            text=payload,
            media_type=media_type,
            media_file_id=media_file_id,          # для фото
            media_file_path=media_file_path,      # для видео
            status="queued",
            total=len(total)
        )
        session.add(bj)
        await session.commit()

    # Кидаем в ARQ
    arq = await _arq()
    await arq.enqueue_job("broadcast_send", job_id)
    
    media_info = ""
    if media_type == "photo":
        media_info = "\n📸 С фотографией"
    elif media_type == "video" and media_file_path:
        file_size_mb = Path(media_file_path).stat().st_size / 1024 / 1024
        media_info = f"\n🎬 С видео ({file_size_mb:.1f} МБ)"
    
    await msg.answer(
        f"🚀 Запустил рассылку <code>#{job_id}</code>{media_info}\n"
        f"Всего пользователей: <b>{bj.total}</b>\n\n"
        f"Команда отмены: <code>/broadcast_cancel {job_id}</code>\n"
        f"Статус: <code>/broadcast_status {job_id}</code>",
        parse_mode="HTML"
    )

@router.message(Command("broadcast_cancel"))
async def cmd_broadcast_cancel(msg: Message):
    if not _is_admin(msg.from_user.id):
        return
    parts = (msg.text or "").split(" ", 1)
    if len(parts) < 2:
        await msg.answer("Использование: <code>/broadcast_cancel JOB_ID</code>", parse_mode="HTML")
        return
    job_id = parts[1].strip()
    async with SessionLocal() as session:
        await session.execute(
            update(BroadcastJob)
            .where(BroadcastJob.id == job_id)
            .values(status="cancelled")
        )
        await session.commit()
    await msg.answer(f"⏹ Отменил рассылку <code>#{job_id}</code>", parse_mode="HTML")

@router.message(Command("broadcast_status"))
async def cmd_broadcast_status(msg: Message):
    if not _is_admin(msg.from_user.id):
        return
    parts = (msg.text or "").split(" ", 1)
    if len(parts) < 2:
        await msg.answer("Использование: <code>/broadcast_status JOB_ID</code>", parse_mode="HTML")
        return
    job_id = parts[1].strip()
    async with SessionLocal() as session:
        row = await session.execute(select(BroadcastJob).where(BroadcastJob.id == job_id))
        bj = row.scalars().first()
    if not bj:
        await msg.answer("❌ Не нашёл такую рассылку")
        return
    
    media_info = ""
    if bj.media_type == "photo":
        media_info = "\n📸 Тип: фото"
    elif bj.media_type == "video":
        media_info = "\n🎬 Тип: видео"
    else:
        media_info = "\n📝 Тип: текст"
    
    await msg.answer(
        f"📊 Рассылка <code>#{bj.id}</code>\n"
        f"Статус: <b>{bj.status}</b>{media_info}\n"
        f"Всего: <b>{bj.total}</b>\n"
        f"Отправлено: <b>{bj.sent}</b>\n"
        f"Ошибок: <b>{bj.failed}</b>\n"
        f"{('Заметка: ' + bj.note) if bj.note else ''}",
        parse_mode="HTML"
    )

# ===== ТЕСТОВЫЕ КОМАНДЫ =====

@router.message(Command("broadcast_test"))
async def cmd_broadcast_test(msg: Message):
    """
    Тестовая рассылка — отправляет только админу
    """
    if not _is_admin(msg.from_user.id):
        return
    
    # Извлекаем текст (из caption для медиа или из text)
    raw_text = (msg.caption or msg.text or "").strip()
    if not raw_text.startswith("/broadcast_test"):
        return
    
    parts = raw_text.split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await msg.answer("Использование: <code>/broadcast_test Текст</code>", parse_mode="HTML")
        return
    
    payload = parts[1].strip()
    
    # Определяем тип медиа
    media_type = None
    media_file_id = None
    
    if msg.photo:
        media_type = "photo"
        media_file_id = msg.photo[-1].file_id
    elif msg.video:
        media_type = "video"
        media_file_id = msg.video.file_id
    
    # Отправляем ТОЛЬКО админу
    try:
        if media_type == "photo" and media_file_id:
            await msg.bot.send_photo(
                msg.from_user.id, 
                photo=media_file_id, 
                caption=f"🧪 ТЕСТ РАССЫЛКИ:\n\n{payload}"
            )
        elif media_type == "video" and media_file_id:
            await msg.bot.send_video(
                msg.from_user.id, 
                video=media_file_id, 
                caption=f"🧪 ТЕСТ РАССЫЛКИ:\n\n{payload}"
            )
        else:
            await msg.answer(f"🧪 ТЕСТ РАССЫЛКИ:\n\n{payload}")
        
        await msg.answer("✅ Тестовое сообщение отправлено вам успешно!")
    except Exception as e:
        await msg.answer(f"❌ Ошибка теста: {e}")