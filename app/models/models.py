# app/models/models.py
from sqlalchemy import Column, Integer, String, BigInteger, DateTime, Text, ForeignKey, func
from sqlalchemy.orm import relationship
from app.repo.db import Base
import uuid
# === USERS из вашей БД ===
class User(Base):
    __tablename__ = "users"
    # В вашей таблице PK = id (CHAR(36)), но бизнес-ключ — user_id (tg id).
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))               # CHAR(36)
    user_id = Column(BigInteger, unique=True, index=True, nullable=False)  # telegram id
    username = Column(Text)                                  # как в схеме
    credits = Column(Integer, nullable=False, default=0)
    is_admin = Column(Integer, default=0)                    # tinyint(1)
    friends_invited = Column(Integer)
    email = Column(Text)
    receipt_opt_out = Column(Integer, default=0)             # tinyint(1)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    locale = Column(String(8), nullable=True)  
    # связи (по user_id!)
    payments = relationship("Payment", back_populates="user", primaryjoin="User.user_id==foreign(Payment.user_id)")
    tasks = relationship("VideoRequest", back_populates="user", primaryjoin="User.user_id==foreign(VideoRequest.user_id)")

# === PAYMENTS (новая таблица) ===
class Payment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)  # FK на users.user_id
    provider_payment_id = Column(String(128), unique=True, nullable=False)
    qty_credits = Column(Integer, nullable=False)
    amount_rub = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="payments", primaryjoin="User.user_id==foreign(Payment.user_id)")

# === VIDEO_REQUESTS из вашей БД ===
class VideoRequest(Base):
    __tablename__ = "video_requests"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    chat_id = Column(BigInteger)

    prompt = Column(Text)
    format = Column(Text)       # храним aspect_ratio "16:9"/"9:16"
    model = Column(Text)        # "veo-3-quality"
    cost = Column(Integer)      # списанные кредиты
    duration = Column(Integer)
    resolution = Column(Text)

    video_url = Column(Text, nullable=True)
    task_id = Column(Text, nullable=True)      # внешний task id из RunBlob
    status = Column(Text, nullable=True)       # pending | processing | success | error

    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    user = relationship("User", back_populates="tasks", primaryjoin="User.user_id==foreign(VideoRequest.user_id)")

class BroadcastJob(Base):
    __tablename__ = "broadcast_jobs"
    id = Column(String(36), primary_key=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    created_by = Column(BigInteger, nullable=False)
    text = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="queued")
    total = Column(Integer, default=0)
    sent = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    fallback = Column(Integer, default=0)
    note = Column(Text)
    media_type = Column(String(20), nullable=True)      # "photo", "video" или NULL
    media_file_id = Column(Text, nullable=True)         # file_id из Telegram
    media_file_path = Column(Text, nullable=True)  