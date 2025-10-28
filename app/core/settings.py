from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Dict, Any, Optional

class Settings(BaseSettings):
    TELEGRAM_TOKEN: str
    WEBHOOK_DOMAIN: str
    WEBHOOK_SECRET: str
    
    BROADCAST_RPS: int = 30         # сообщений/сек (безопасное значение)
    BROADCAST_CONCURRENCY: int = 50 # одновременных задач
    BROADCAST_BATCH: int = 2000     # fetch из БД за раз


    GREETING_IMAGE_PATH: str = "app/assets/welcome.jpg"
    GREETING_IMAGE_URL: Optional[str] = None
    
    VAT_CODE: Optional[int] = None            # <— ДОБАВЛЕНО
    TAX_SYSTEM_CODE: Optional[int] = None     # <— ДОБАВЛЕНО
    RECEIPT_FALLBACK_EMAIL: Optional[str] = None  # <— ДОБА

    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str

    REDIS_URL: str
    REDIS_PASSWORD: str | None = None

    # YooKassa
    YOOKASSA_SHOP_ID: Optional[str] = None
    YOOKASSA_SECRET_KEY: Optional[str] = None
    YOOKASSA_WEBHOOK_SECRET: Optional[str] = None
    YOOKASSA_RECEIPT_ENABLED: bool = False

    # Планы из .env (pydantic умеет парсить JSON-строки в dict)
    SUBSCRIPTION_PLANS_RUBS: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    SUBSCRIPTION_PLANS_STARS: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    COST_CREDITS_FAST: int = 1
    COST_CREDITS_QUALITY: int = 1

    RUNBLOB_BASE_URL: str = "https://api.runblob.com"

    EXAMPLES_URL: Optional[str] = None
    GUIDE_URL: Optional[str] = None
    SUPPORT_URL: Optional[str] = None

    RUNBLOB_API_KEY: str

    DEBUG: bool = False
    ADMIN_ID: Optional[int] = None

    # старые поля оставляем для обратной совместимости (не используются в новой оплате)
    PRICE_SINGLE_RUB: int = 199
    PACKAGE_OPTIONS_RUB: str = "5:899,10:1590,20:2890"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def SQLALCHEMY_URL(self) -> str:
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
            "?charset=utf8mb4"
        )

    def webhook_base(self) -> str:
        return self.WEBHOOK_DOMAIN.rstrip("/")

settings = Settings()
