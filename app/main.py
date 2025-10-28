# app/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.bot.init import bot, redis_pool
from app.core.db import engine
from app.core.logger import logger
from app.core.settings import settings
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.request_id import RequestIdMiddleware

# Роутеры
from app.api.routers.telegram import router as telegram_router
from app.api.routers.yookassa import router as yookassa_router
from app.api.routers.runblob import router as runblob_router

ALLOWED_UPDATES = [
    "message", 
    "edited_message", 
    "callback_query",
    "pre_checkout_query", 
    "successful_payment",
]


def _build_webhook_url() -> str:
    base = settings.webhook_base()
    return f"{base}/webhook/telegram"


def _assert_https_domain(url: str) -> None:
    if not url.startswith("https://"):
        raise RuntimeError("WEBHOOK_DOMAIN must be HTTPS (required by Telegram).")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("📦 Lifespan start")

    # DB ping
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
        logger.info("✅ DB connected")

    # Telegram webhook
    webhook_url = _build_webhook_url()
    _assert_https_domain(webhook_url)

    await bot.set_webhook(
        url=webhook_url,
        secret_token=settings.WEBHOOK_SECRET,
        drop_pending_updates=True,
        allowed_updates=ALLOWED_UPDATES,
        max_connections=50,
    )
    logger.info(f"📡 Webhook set: {webhook_url}")

    # Redis ping (если включён)
    if redis_pool:
        await redis_pool.ping()
        logger.info("✅ Redis connected")

    # ---- set bot commands (RU/EN combined descriptions) ----
    # try:
    #     from aiogram.types import BotCommand
    #     await bot.set_my_commands([
    #         BotCommand(command="start",         description="Открыть меню / Open menu"),
    #         BotCommand(command="create_video", description="Создать видео / Create video"),
    #         BotCommand(command="buy",          description="Купить генерации / Buy generations"),
    #         BotCommand(command="example",      description="Примеры / Examples"),
    #         # BotCommand(command="invite_friend",description="Пригласить друга (+1) / Invite a friend"),
    #         BotCommand(command="bots",         description="Наши боты / Our bots"),
    #         BotCommand(command="help",         description="Инструкция / Help")
    #     ])
    #     logger.info("✅ Bot commands set: /create_video, /menu, /buy, /help")
    # except Exception as e:
    #     logger.warning(f"Couldn't set commands: {e}")

    # ---- app is running ----
    yield

    # ---- shutdown ----
    logger.info("🧹 Lifespan shutdown")
    try:
        await bot.delete_webhook(drop_pending_updates=False)
    except Exception as e:
        logger.warning(f"⚠️ delete_webhook: {e}")
    try:
        await bot.session.close()
    except Exception as e:
        logger.warning(f"⚠️ bot.session.close: {e}")
    try:
        if redis_pool:
            await redis_pool.aclose()
    except Exception as e:
        logger.warning(f"⚠️ redis_pool.aclose: {e}")


app = FastAPI(title="Veo 3.1 Studio Bot", lifespan=lifespan)

# Middleware
app.add_middleware(RequestIdMiddleware)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.WEBHOOK_DOMAIN], 
    allow_credentials=False,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

app.include_router(telegram_router, prefix="/webhook")    # /webhook/telegram
app.include_router(yookassa_router, prefix="/webhook")   # /webhook/yookassa
app.include_router(runblob_router,  prefix="/webhook")   # /webhook/runblob
