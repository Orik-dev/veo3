# from __future__ import annotations

# from fastapi import APIRouter, Request, Response, HTTPException, Depends
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select

# from app.repo.db import get_session
# from app.core.settings import settings
# from app.core.logger import logger
# from app.domain.generation.service_finalize import finalize_by_callback
# from app.models.models import VideoRequest
# from app.bot.init import bot

# # Диагностика/загрузка
# from aiogram.exceptions import TelegramBadRequest, TelegramMigrateToChat
# from aiogram.types import BufferedInputFile
# import aiohttp
# import asyncio
# import html

# # Для человекочитаемых ошибок
# from app.domain.generation.clients.runblob import _pick_code_and_detail
# from app.domain.generation.error import to_user_message

# router = APIRouter()


# def _ok_token(token: str | None) -> bool:
#     if not token:
#         return False
#     from hmac import compare_digest
#     try:
#         return compare_digest(token, settings.WEBHOOK_SECRET)
#     except Exception:
#         return False


# MAX_CAPTION = 1024


# def _safe_caption(text: str) -> str:
#     if text is None:
#         return "🎥 Ваше видео готово."
#     clean = html.escape(str(text), quote=False)
#     pref = "🎥 Ваше видео по запросу: "
#     budget = MAX_CAPTION - len(pref)
#     if budget < 10:
#         budget = MAX_CAPTION
#         pref = ""
#     if len(clean) > budget:
#         clean = clean[: max(0, budget - 1)] + "…"
#     return f"{pref}{clean}" if pref else clean


# async def _head_ok(url: str, timeout: float = 10.0) -> tuple[bool, int | None, str | None]:
#     """Быстрая проверка доступности URL для Telegram."""
#     try:
#         async with aiohttp.ClientSession() as s:
#             async with s.head(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=timeout)) as r:
#                 ct = r.headers.get("Content-Type")
#                 cl = r.headers.get("Content-Length")
#                 size = int(cl) if cl and cl.isdigit() else None
#                 return (200 <= r.status < 300, size, ct)
#     except Exception:
#         return (False, None, None)


# async def _send_video_resilient(chat_id: int | str, video_url: str, caption: str) -> None:
#     """
#     1) Пытаемся отправить по URL.
#     2) Если Telegram ругается — скачиваем и отправляем как файл.
#     3) Если всё упало — отправляем ссылку; если и это падает, шлём короткое текстовое.
#     """
#     # 1. Прямая отправка по URL
#     try:
#         await bot.send_video(
#             chat_id=chat_id,
#             video=video_url,
#             caption=caption,
#             request_timeout=120,
#         )
#         return
#     except TelegramMigrateToChat as e:
#         logger.warning("Chat migrated to %s", e.migrate_to_chat_id)
#         await bot.send_video(
#             chat_id=e.migrate_to_chat_id,
#             video=video_url,
#             caption=caption,
#             request_timeout=120,
#         )
#         return
#     except TelegramBadRequest as e:
#         logger.error("TelegramBadRequest on send_video URL: %s", e.message)
#         if "can't parse entities" in (e.message or "") or "message is too long" in (e.message or ""):
#             try:
#                 await bot.send_video(chat_id=chat_id, video=video_url, caption=_safe_caption(caption), request_timeout=120)
#                 return
#             except TelegramBadRequest as e2:
#                 logger.error("Retry with trimmed caption failed: %s", e2.message)
#     except Exception as e:
#         logger.exception("Unexpected error on send_video URL: %r", e)

#     # 2. Скачиваем и отправляем как файл
#     ok, size, ct = await _head_ok(video_url)
#     logger.info("HEAD check: ok=%s size=%s content_type=%s", ok, size, ct)

#     try:
#         async with aiohttp.ClientSession() as s:
#             async with s.get(video_url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=180)) as r:
#                 r.raise_for_status()
#                 data = await r.read()
#                 fin = BufferedInputFile(data, filename="video.mp4")
#                 await bot.send_video(chat_id=chat_id, video=fin, caption=caption, request_timeout=180)
#                 return
#     except TelegramBadRequest as e:
#         logger.error("TelegramBadRequest on send_video file: %s", e.message)
#     except Exception:
#         logger.exception("Failed to fetch and send as file")

#     # 3. Текст + ссылка → короткое текстовое
#     try:
#         await bot.send_message(chat_id, f"{caption}\n{video_url}")
#     except Exception:
#         logger.exception("Fallback send_message with URL failed")
#         try:
#             await bot.send_message(chat_id, _safe_caption(caption))
#         except Exception:
#             logger.exception("Final fallback send_message failed")


# @router.post("/runblob")
# async def runblob_webhook(request: Request, session: AsyncSession = Depends(get_session)):
#     token = request.query_params.get("token")
#     if not _ok_token(token):
#         raise HTTPException(403, "Forbidden")

#     try:
#         data = await request.json()
#     except Exception:
#         logger.exception("RunBlob webhook: failed to parse JSON")
#         return Response(status_code=204)

#     logger.info("RunBlob webhook: %s", data)

#     task_id = data.get("task_id") or data.get("id")
#     success = bool(data.get("success"))
#     video_url = data.get("video_url") or data.get("url")

#     if not task_id:
#         return Response(status_code=204)

#     # Обновляем состояние задачи; при error внутри будет произведён рефанд
#     try:
#         updated = await finalize_by_callback(
#             session,
#             runblob_task_id=task_id,
#             status="success" if success else "error",
#             url=video_url,
#         )
#     except Exception:
#         logger.exception("RunBlob webhook: finalize_by_callback failed")
#         return Response(status_code=204)

#     if updated:
#         try:
#             res = await session.execute(select(VideoRequest).where(VideoRequest.task_id == task_id))
#             vr: VideoRequest | None = res.scalars().first()
#             if vr and vr.chat_id:
#                 if success and video_url:
#                     caption = _safe_caption(vr.prompt or "—")
#                     try:
#                         await _send_video_resilient(chat_id=vr.chat_id, video_url=video_url, caption=caption)
#                     except TelegramBadRequest as e:
#                         logger.error("Final TelegramBadRequest: %s", e.message)
#                         await bot.send_message(vr.chat_id, f"{caption}\n{video_url}")
#                 else:
#                     # Разобрать код ошибки и отдать понятный текст + сумма возврата
#                     code, _detail = _pick_code_and_detail(data.get("message"), "TASK_FAILED")
#                     user_text = to_user_message(code)
#                     tip = ""
#                     if code in {"GOOGLE_DECLINED", "TASK_FAILED"}:
#                         tip = "\n🛠 Попробуйте изменить описание (промт) или прикрепить другое фото."
#                     try:
#                         await bot.send_message(
#                             vr.chat_id,
#                             f"❌ {user_text}\n\n💸 Возвращено: {vr.cost} генераций.{tip}"
#                         )
#                     except Exception:
#                         logger.exception("RunBlob webhook: failed to notify user (error case)")
#         except Exception:
#             logger.exception("RunBlob webhook: failed to notify user")

#     return Response(status_code=204)


# from __future__ import annotations

# from fastapi import APIRouter, Request, Response, HTTPException, Depends
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select

# from app.repo.db import get_session
# from app.core.settings import settings
# from app.core.logger import logger
# from app.domain.generation.service_finalize import finalize_by_callback
# from app.models.models import VideoRequest
# from app.bot.init import bot

# # Диагностика/загрузка
# from aiogram.exceptions import TelegramBadRequest, TelegramMigrateToChat
# from aiogram.types import BufferedInputFile
# import aiohttp
# import asyncio
# import html

# # Для человекочитаемых ошибок
# from app.domain.generation.clients.runblob import _pick_code_and_detail
# from app.domain.generation.error import to_user_message

# router = APIRouter()


# def _ok_token(token: str | None) -> bool:
#     if not token:
#         return False
#     from hmac import compare_digest
#     try:
#         return compare_digest(token, settings.WEBHOOK_SECRET)
#     except Exception:
#         return False


# MAX_CAPTION = 1024


# def _safe_caption(text: str) -> str:
#     if text is None:
#         return "🎥 Ваше видео готово."
#     clean = html.escape(str(text), quote=False)
#     pref = "🎥 Ваше видео по запросу: "
#     budget = MAX_CAPTION - len(pref)
#     if budget < 10:
#         budget = MAX_CAPTION
#         pref = ""
#     if len(clean) > budget:
#         clean = clean[: max(0, budget - 1)] + "…"
#     return f"{pref}{clean}" if pref else clean


# async def _head_ok(url: str, timeout: float = 10.0) -> tuple[bool, int | None, str | None]:
#     """Быстрая проверка доступности URL для Telegram."""
#     try:
#         async with aiohttp.ClientSession() as s:
#             async with s.head(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=timeout)) as r:
#                 ct = r.headers.get("Content-Type")
#                 cl = r.headers.get("Content-Length")
#                 size = int(cl) if cl and cl.isdigit() else None
#                 return (200 <= r.status < 300, size, ct)
#     except Exception:
#         return (False, None, None)


# async def _download(url: str, timeout_total: float = 180) -> bytes:
#     async with aiohttp.ClientSession() as s:
#         async with s.get(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=timeout_total)) as r:
#             r.raise_for_status()
#             return await r.read()


# async def _send_video_resilient(chat_id: int | str, video_url: str, caption: str) -> None:
#     """
#     Гарантируем, что отправляем именно VIDEO, даже если ролик без аудио:
#     1) Сначала пробуем URL через send_video(supports_streaming=True).
#     2) Если Телеграм не принял — скачиваем и отправляем как файл через send_video (имя .mp4).
#     3) Если совсем плохо — отправляем текст + ссылку (никаких send_animation).
#     """
#     # 1) Прямая отправка по URL — ИМЕННО как видео
#     try:
#         await bot.send_video(
#             chat_id=chat_id,
#             video=video_url,
#             caption=caption,
#             supports_streaming=True,   # <— помогает клиентам показывать как видео
#             request_timeout=120,
#         )
#         return
#     except TelegramMigrateToChat as e:
#         logger.warning("Chat migrated to %s", e.migrate_to_chat_id)
#         await bot.send_video(
#             chat_id=e.migrate_to_chat_id,
#             video=video_url,
#             caption=caption,
#             supports_streaming=True,
#             request_timeout=120,
#         )
#         return
#     except TelegramBadRequest as e:
#         logger.error("TelegramBadRequest on send_video URL: %s", e.message)
#         # иногда проблема в подписи — попробуем укороченную
#         if "can't parse entities" in (e.message or "") or "message is too long" in (e.message or ""):
#             try:
#                 await bot.send_video(
#                     chat_id=chat_id,
#                     video=video_url,
#                     caption=_safe_caption(caption),
#                     supports_streaming=True,
#                     request_timeout=120,
#                 )
#                 return
#             except TelegramBadRequest as e2:
#                 logger.error("Retry with trimmed caption failed: %s", e2.message)
#     except Exception as e:
#         logger.exception("Unexpected error on send_video URL: %r", e)

#     # 2) Скачиваем и отправляем как файл В ФОРМЕ ВИДЕО (не animation)
#     ok, size, ct = await _head_ok(video_url)
#     logger.info("HEAD check: ok=%s size=%s content_type=%s", ok, size, ct)

#     try:
#         data = await _download(video_url, timeout_total=180)
#         # ВАЖНО: имя файла с .mp4 — Телеграм надёжнее распознаёт как видео
#         fin = BufferedInputFile(data, filename="video.mp4")
#         await bot.send_video(
#             chat_id=chat_id,
#             video=fin,
#             caption=caption,
#             supports_streaming=True,
#             request_timeout=180,
#         )
#         return
#     except TelegramBadRequest as e:
#         logger.error("TelegramBadRequest on send_video(file): %s", e.message)
#     except Exception:
#         logger.exception("Failed to fetch and send as file")

#     # 3) Фоллбек: текст + ссылка (НО НЕ send_animation)
#     try:
#         await bot.send_message(chat_id, f"{_safe_caption(caption)}\n{video_url}")
#     except Exception:
#         logger.exception("Fallback send_message with URL failed")
#         try:
#             await bot.send_message(chat_id, _safe_caption(caption))
#         except Exception:
#             logger.exception("Final fallback send_message failed")


# @router.post("/runblob")
# async def runblob_webhook(request: Request, session: AsyncSession = Depends(get_session)):
#     token = request.query_params.get("token")
#     if not _ok_token(token):
#         raise HTTPException(403, "Forbidden")

#     try:
#         data = await request.json()
#     except Exception:
#         logger.exception("RunBlob webhook: failed to parse JSON")
#         return Response(status_code=204)

#     logger.info("RunBlob webhook: %s", data)

#     task_id = data.get("task_id") or data.get("id")
#     success = bool(data.get("success"))
#     video_url = data.get("video_url") or data.get("url")

#     if not task_id:
#         return Response(status_code=204)

#     # Обновляем состояние задачи; при error внутри будет произведён рефанд
#     try:
#         updated = await finalize_by_callback(
#             session,
#             runblob_task_id=task_id,
#             status="success" if success else "error",
#             url=video_url,
#         )
#     except Exception:
#         logger.exception("RunBlob webhook: finalize_by_callback failed")
#         return Response(status_code=204)

#     if updated:
#         try:
#             res = await session.execute(select(VideoRequest).where(VideoRequest.task_id == task_id))
#             vr: VideoRequest | None = res.scalars().first()
#             if vr and vr.chat_id:
#                 if success and video_url:
#                     caption = _safe_caption(vr.prompt or "—")
#                     try:
#                         await _send_video_resilient(chat_id=vr.chat_id, video_url=video_url, caption=caption)
#                     except TelegramBadRequest as e:
#                         logger.error("Final TelegramBadRequest: %s", e.message)
#                         await bot.send_message(vr.chat_id, f"{caption}\n{video_url}")
#                 else:
#                     # Разобрать код ошибки и отдать понятный текст + сумма возврата
#                     code, _detail = _pick_code_and_detail(data.get("message"), "TASK_FAILED")
#                     user_text = to_user_message(code)
#                     tip = ""
#                     if code in {"GOOGLE_DECLINED", "TASK_FAILED"}:
#                         tip = "\n🛠 Попробуйте изменить описание (промт) или прикрепить другое фото."
#                     try:
#                         await bot.send_message(
#                             vr.chat_id,
#                             f"❌ {user_text}\n\n💸 Возвращено: {vr.cost} генераций.{tip}"
#                         )
#                     except Exception:
#                         logger.exception("RunBlob webhook: failed to notify user (error case)")
#         except Exception:
#             logger.exception("RunBlob webhook: failed to notify user")

#     return Response(status_code=204)


# app/webhooks/runblob.py
from __future__ import annotations

from fastapi import APIRouter, Request, Response, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.repo.db import get_session
from app.core.settings import settings
from app.core.logger import logger
from app.domain.generation.service_finalize import finalize_by_callback
from app.models.models import VideoRequest
from app.bot.init import bot

# Диагностика/загрузка
from aiogram.exceptions import TelegramBadRequest, TelegramMigrateToChat
from aiogram.types import BufferedInputFile
import aiohttp
import asyncio
import html
import os
import shutil
import tempfile
import subprocess

# Для человекочитаемых ошибок
from app.domain.generation.clients.runblob import _pick_code_and_detail
from app.domain.generation.error import to_user_message

router = APIRouter()


def _ok_token(token: str | None) -> bool:
    if not token:
        return False
    from hmac import compare_digest
    try:
        return compare_digest(token, settings.WEBHOOK_SECRET)
    except Exception:
        return False


MAX_CAPTION = 1024


def _safe_caption(text: str) -> str:
    if text is None:
        return "🎥 Ваше видео готово."
    clean = html.escape(str(text), quote=False)
    pref = "🎥 Ваше видео по запросу: "
    budget = MAX_CAPTION - len(pref)
    if budget < 10:
        budget = MAX_CAPTION
        pref = ""
    if len(clean) > budget:
        clean = clean[: max(0, budget - 1)] + "…"
    return f"{pref}{clean}" if pref else clean


async def _head_ok(url: str, timeout: float = 10.0) -> tuple[bool, int | None, str | None]:
    """Быстрая проверка доступности URL для Telegram."""
    try:
        async with aiohttp.ClientSession() as s:
            async with s.head(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=timeout)) as r:
                ct = r.headers.get("Content-Type")
                cl = r.headers.get("Content-Length")
                size = int(cl) if cl and cl.isdigit() else None
                return (200 <= r.status < 300, size, ct)
    except Exception:
        return (False, None, None)


def _ffmpeg_exists() -> bool:
    return bool(shutil.which("ffmpeg"))


def _mux_silent_audio(src_path: str) -> str | None:
    """
    Добавляет немую аудиодорожку к видео, чтобы Telegram показал именно ПЛЕЕР.
    Требует установленный ffmpeg в контейнере.
    Возвращает путь к новому файлу или None при ошибке.
    """
    if not _ffmpeg_exists():
        return None
    out_path = src_path.rsplit(".", 1)[0] + ".with_audio.mp4"
    cmd = [
        "ffmpeg",
        "-y",
        "-i", src_path,
        "-f", "lavfi",
        "-tune", "stillimage",
        "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-shortest",
        "-c:v", "copy",            # без перекодирования видео
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        out_path,
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return out_path
    except Exception:
        logger.exception("ffmpeg mux_silent_audio failed")
        with contextlib.suppress(Exception):
            os.remove(out_path)
        return None


async def _send_video_resilient(chat_id: int | str, video_url: str, caption: str) -> None:
    """
    1) Пытаемся отправить по URL как видео (supports_streaming=True).
    2) Если Telegram ругается или превращает в GIF — качаем файл.
       2.1) Если есть ffmpeg — примиксовываем немую дорожку и отправляем как видео.
       2.2) Если ffmpeg нет или шаг 2.1 упал — отправляем как документ (mp4), чтобы НЕ было "GIF".
    3) Если всё упало — отправляем ссылку; если и это падает, шлём короткий текст.
    """
    # 1. Прямая отправка по URL
    try:
        await bot.send_video(
            chat_id=chat_id,
            video=video_url,
            caption=caption,
            supports_streaming=True,
            request_timeout=120,
        )
        return
    except TelegramMigrateToChat as e:
        logger.warning("Chat migrated to %s", e.migrate_to_chat_id)
        await bot.send_video(
            chat_id=e.migrate_to_chat_id,
            video=video_url,
            caption=caption,
            supports_streaming=True,
            request_timeout=120,
        )
        return
    except TelegramBadRequest as e:
        logger.error("TelegramBadRequest on send_video URL: %s", e.message)
        if "can't parse entities" in (e.message or "") or "message is too long" in (e.message or ""):
            try:
                await bot.send_video(
                    chat_id=chat_id,
                    video=video_url,
                    caption=_safe_caption(caption),
                    supports_streaming=True,
                    request_timeout=120,
                )
                return
            except TelegramBadRequest as e2:
                logger.error("Retry with trimmed caption failed: %s", e2.message)
    except Exception as e:
        logger.exception("Unexpected error on send_video URL: %r", e)

    # 2. Скачиваем файл
    ok, size, ct = await _head_ok(video_url)
    logger.info("HEAD check: ok=%s size=%s content_type=%s", ok, size, ct)

    tmpdir = tempfile.mkdtemp(prefix="veo3_")
    src_path = os.path.join(tmpdir, "video.mp4")
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(video_url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=240)) as r:
                r.raise_for_status()
                with open(src_path, "wb") as f:
                    async for chunk in r.content.iter_chunked(1 << 16):
                        f.write(chunk)
    except Exception:
        logger.exception("Failed to download video for local resend")
        # Попробуем хотя бы документом по URL
        try:
            await bot.send_document(chat_id=chat_id, document=video_url, caption=caption, request_timeout=120)
            return
        except Exception:
            logger.exception("send_document by URL failed too")

    try:
        # 2.1 Попытка примиксовать немую дорожку
        send_path = src_path
        if _ffmpeg_exists():
            new_path = _mux_silent_audio(src_path)
            if new_path:
                send_path = new_path

        # Пытаемся как ВИДЕО (BufferedInputFile гарантирует корректный mime)
        with open(send_path, "rb") as f:
            fin = BufferedInputFile(f.read(), filename=os.path.basename(send_path))
        try:
            await bot.send_video(
                chat_id=chat_id,
                video=fin,
                caption=caption,
                supports_streaming=True,
                request_timeout=240,
            )
            return
        except TelegramBadRequest as e:
            logger.error("TelegramBadRequest on send_video file: %s", e.message)

        # 2.2 Фоллбек — как документ (это точно не GIF)
        with open(send_path, "rb") as f2:
            fin2 = BufferedInputFile(f2.read(), filename=os.path.basename(send_path))
        await bot.send_document(chat_id=chat_id, document=fin2, caption=caption, request_timeout=240)
        return

    except Exception:
        logger.exception("Failed to send local file as video/document")
    finally:
        try:
            shutil.rmtree(tmpdir, ignore_errors=True)
        except Exception:
            pass

    # 3. Последний фоллбек
    try:
        await bot.send_message(chat_id, f"{caption}\n{video_url}")
    except Exception:
        logger.exception("Fallback send_message with URL failed")
        try:
            await bot.send_message(chat_id, _safe_caption(caption))
        except Exception:
            logger.exception("Final fallback send_message failed")


@router.post("/runblob")
async def runblob_webhook(request: Request, session: AsyncSession = Depends(get_session)):
    token = request.query_params.get("token")
    if not _ok_token(token):
        raise HTTPException(403, "Forbidden")

    try:
        data = await request.json()
    except Exception:
        logger.exception("RunBlob webhook: failed to parse JSON")
        return Response(status_code=204)

    logger.info("RunBlob webhook: %s", data)

    task_id = data.get("task_id") or data.get("id")
    success = bool(data.get("success"))
    video_url = data.get("video_url") or data.get("url")

    if not task_id:
        return Response(status_code=204)

    # Обновляем состояние задачи; при error внутри будет произведён рефанд
    try:
        updated = await finalize_by_callback(
            session,
            runblob_task_id=task_id,
            status="success" if success else "error",
            url=video_url,
        )
    except Exception:
        logger.exception("RunBlob webhook: finalize_by_callback failed")
        return Response(status_code=204)

    if updated:
        try:
            res = await session.execute(select(VideoRequest).where(VideoRequest.task_id == task_id))
            vr: VideoRequest | None = res.scalars().first()
            if vr and vr.chat_id:
                if success and video_url:
                    caption = _safe_caption(vr.prompt or "—")
                    try:
                        await _send_video_resilient(chat_id=vr.chat_id, video_url=video_url, caption=caption)
                    except TelegramBadRequest as e:
                        logger.error("Final TelegramBadRequest: %s", e.message)
                        await bot.send_message(vr.chat_id, f"{caption}\n{video_url}")
                else:
                    # Разобрать код ошибки и отдать понятный текст + сумма возврата
                    code, _detail = _pick_code_and_detail(data.get("message"), "TASK_FAILED")
                    user_text = to_user_message(code)
                    tip = ""
                    if code in {"GOOGLE_DECLINED", "TASK_FAILED"}:
                        tip = "\n🛠 Попробуйте изменить описание (промт) или прикрепить другое фото."
                    try:
                        await bot.send_message(
                            vr.chat_id,
                            f"❌ {user_text}\n\n💸 Возвращено: {vr.cost} генераций.{tip}"
                        )
                    except Exception:
                        logger.exception("RunBlob webhook: failed to notify user (error case)")
        except Exception:
            logger.exception("RunBlob webhook: failed to notify user")

    return Response(status_code=204)
