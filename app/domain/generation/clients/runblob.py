from __future__ import annotations

import asyncio
import random
from typing import Any, Dict, Optional, Tuple

import aiohttp

from app.core.settings import settings
from app.core.logger import logger

BASE = settings.RUNBLOB_BASE_URL.rstrip("/")
AUTH_HEADER = {"Authorization": f"Bearer {settings.RUNBLOB_API_KEY}"}
JSON_HEADERS = {"Content-Type": "application/json", **AUTH_HEADER}

KNOWN_CODES = {
    "INSUFFICIENT_CREDITS",
    "NON_ENGLISH_PROMPT",
    "UNSAFE_CONTENT",
    "PROMINENT_PEOPLE_UPLOAD",
    "PHOTOREAL_UPLOAD",
    "MODERATION_FAILED",
    "GOOGLE_DECLINED",
    "TASK_FAILED",
    "TASK_NOT_FOUND",
    "INVALID_TASK_ID",
    "TIMEOUT",
    "MAINTENANCE",
    "INVALID_IMAGE",
    "IMAGE_TOO_LARGE",
    "UNSUPPORTED_IMAGE_FORMAT",
}


class RunBlobError(Exception):
    def __init__(self, code: str, message: Optional[str] = None, http_status: Optional[int] = None):
        super().__init__(message or code)
        self.code = code
        self.http_status = http_status
        self.message = message or code

    def __str__(self) -> str:
        base = self.code
        if self.http_status:
            base += f" (HTTP {self.http_status})"
        if self.message and self.message != self.code:
            base += f": {self.message}"
        return base


def _pick_code_and_detail(raw_message: Any, fallback_code: str = "TASK_FAILED") -> Tuple[str, str]:
    if isinstance(raw_message, str):
        msg = raw_message.strip()
        upper = msg.upper()
        if upper in KNOWN_CODES:
            return upper, msg
        if all(ch.isupper() or ch.isdigit() or ch == "_" for ch in upper) and "_" in upper:
            return upper, msg
        return fallback_code, msg
    return fallback_code, str(raw_message)


def _default_timeout() -> aiohttp.ClientTimeout:
    return aiohttp.ClientTimeout(
        total=None,
        connect=10,
        sock_connect=10,
        sock_read=90,
    )


async def _post_json_with_retries(
    session: aiohttp.ClientSession,
    url: str,
    headers: Dict[str, str],
    payload: Dict[str, Any],
    *,
    attempts: int = 4,
    base_backoff: float = 1.5,
) -> Tuple[int, Dict[str, Any]]:
    backoff = base_backoff
    for i in range(attempts):
        try:
            async with session.post(url, headers=headers, json=payload) as r:
                try:
                    data = await r.json(content_type=None)
                except Exception:
                    data = {"message": (await r.text())}

                if r.status == 429 or 500 <= r.status < 600:
                    raise aiohttp.ClientResponseError(r.request_info, r.history, status=r.status)

                return r.status, data

        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            is_last = (i == attempts - 1)
            logger.warning(
                "runblob POST retry %s/%s url=%s err=%r",
                i + 1, attempts, url, e
            )
            if is_last:
                raise
            await asyncio.sleep(backoff + random.random())
            backoff *= 2

    raise asyncio.TimeoutError("Exhausted POST retries")


async def _get_json_with_retries(
    session: aiohttp.ClientSession,
    url: str,
    headers: Dict[str, str],
    *,
    attempts: int = 4,
    base_backoff: float = 1.2,
) -> Tuple[int, Dict[str, Any]]:
    backoff = base_backoff
    for i in range(attempts):
        try:
            async with session.get(url, headers=headers) as r:
                try:
                    data = await r.json(content_type=None)
                except Exception:
                    data = {"message": (await r.text())}

                if r.status == 429 or 500 <= r.status < 600:
                    raise aiohttp.ClientResponseError(r.request_info, r.history, status=r.status)

                return r.status, data

        except (asyncio.TimeoutError, aiohttp.ClientError) as e:
            is_last = (i == attempts - 1)
            logger.warning(
                "runblob GET retry %s/%s url=%s err=%r",
                i + 1, attempts, url, e
            )
            if is_last:
                raise
            await asyncio.sleep(backoff + random.random())
            backoff *= 2

    raise asyncio.TimeoutError("Exhausted GET retries")


async def generate(
    *,
    prompt: str,
    model_type: str = "veo-3-fast",
    aspect_ratio: str = "16:9",
    callback_url: Optional[str] = None,
    bytes_image_b64: Optional[str] = None,
    seed: Optional[int] = None,
    filter_text: Optional[str] = "translate",
    session: Optional[aiohttp.ClientSession] = None,
    raise_for_status: bool = True,
    timeout_seconds: int = 90,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "prompt": prompt,
        "model_type": model_type,
        "aspect_ratio": aspect_ratio,
    }
    if callback_url:
        payload["callback_url"] = callback_url

    if bytes_image_b64:
        s = bytes_image_b64.strip()
        if s.startswith("data:"):
            s = s.split(",", 1)[1].strip()
        payload["bytes_image"] = s

        try:
            approx_kb = int(len(s) * 0.75 // 1024) if not s.startswith("http") else 0
            logger.info("runblob.generate: bytes_image set (%s)", "url" if s.startswith("http") else f"~{approx_kb} KB")
        except Exception:
            pass

    if seed is not None:
        payload["seed"] = seed
    if filter_text is not None:
        payload["filter_text"] = filter_text

    url = f"{BASE}/v1/veo/generate"

    close_session = False
    if session is None:
        timeout = _default_timeout()
        if timeout_seconds and timeout_seconds > 0:
            timeout = aiohttp.ClientTimeout(
                total=timeout_seconds, connect=10, sock_connect=10, sock_read=max(60, timeout_seconds - 5)
            )
        session = aiohttp.ClientSession(timeout=timeout)
        close_session = True

    try:
        status, data = await _post_json_with_retries(session, url, JSON_HEADERS, payload, attempts=4)

        # ✅ ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ ОТВЕТА API
        logger.info(f"RunBlob /generate response: HTTP {status}, data={data}")

        # ✅ ИСПРАВЛЕНО: Проверяем разные варианты успешного ответа
        # RunBlob может вернуть либо success=true, либо сразу generation_id/task_id
        has_success_field = data.get("success") is True
        has_task_id = bool(data.get("task_id"))
        has_generation_id = bool(data.get("generation_id"))
        
        is_success = has_success_field or has_task_id or has_generation_id
        
        if status >= 400 or not is_success:
            code, detail = _pick_code_and_detail(data.get("message"), fallback_code="TASK_FAILED")
            logger.warning(f"RunBlob /generate failed: code={code}, detail={detail}, full_response={data}")
            if raise_for_status:
                raise RunBlobError(code=code, message=detail, http_status=status)
            return {"ok": False, "error": code, "detail": detail, "http_status": status, "raw": data}

        # ✅ ИСПРАВЛЕНО: Извлекаем task_id из разных возможных полей
        task_id = data.get("task_id") or data.get("generation_id") or data.get("id")
        
        logger.info(f"RunBlob /generate success: task_id={task_id}")
        
        return {"ok": True, "task_id": task_id, **data}

    except (asyncio.TimeoutError, aiohttp.ClientError) as ce:
        logger.error(f"RunBlob /generate network error: {ce}")
        if raise_for_status:
            raise RunBlobError(code="GOOGLE_DECLINED", message=str(ce))
        return {"ok": False, "error": "GOOGLE_DECLINED", "detail": str(ce)}
    finally:
        if close_session:
            await session.close()


async def status(
    task_id: str,
    *,
    session: Optional[aiohttp.ClientSession] = None,
    raise_for_status: bool = True,
    timeout_seconds: int = 30,
) -> Dict[str, Any]:
    url = f"{BASE}/v1/veo/status/{task_id}"

    close_session = False
    if session is None:
        timeout = _default_timeout()
        if timeout_seconds and timeout_seconds > 0:
            timeout = aiohttp.ClientTimeout(
                total=timeout_seconds, connect=10, sock_connect=10, sock_read=max(10, timeout_seconds - 5)
            )
        session = aiohttp.ClientSession(timeout=timeout)
        close_session = True

    try:
        status_code, data = await _get_json_with_retries(session, url, AUTH_HEADER, attempts=3)

        # ✅ ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ
        logger.info(f"RunBlob /status response: HTTP {status_code}, data={data}")

        if status_code >= 400:
            if raise_for_status:
                raise RunBlobError(code="TASK_NOT_FOUND", message=str(data), http_status=status_code)
            return {"ok": False, "error": "TASK_NOT_FOUND", "detail": str(data), "http_status": status_code, "raw": data}

        status_ = (data.get("status") or "").lower()
        if status_ == "failed":
            code, detail = _pick_code_and_detail(data.get("message"), fallback_code="TASK_FAILED")
            if raise_for_status:
                raise RunBlobError(code=code, message=detail, http_status=status_code)
            return {"ok": False, "error": code, "detail": detail, "http_status": status_code, "raw": data}

        return {"ok": True, **data}

    except (asyncio.TimeoutError, aiohttp.ClientError) as ce:
        if raise_for_status:
            raise RunBlobError(code="GOOGLE_DECLINED", message=str(ce))
        return {"ok": False, "error": "GOOGLE_DECLINED", "detail": str(ce)}
    finally:
        if close_session:
            await session.close()