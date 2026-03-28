from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, create_engine
)
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import DATABASE_URL

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    trackings = relationship("Tracking", back_populates="user", cascade="all, delete-orphan")
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")


class Tracking(Base):
    __tablename__ = "trackings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    url = Column(String(2048), nullable=False)
    name = Column(String(255), default="")
    selector = Column(String(512), nullable=False)
    selector_type = Column(String(20), default="css")  # css, xpath, text
    last_value = Column(Text, default=None, nullable=True)
    last_checked = Column(DateTime, default=None, nullable=True)
    is_changed = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    check_interval_minutes = Column(Integer, default=10)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="trackings")
    logs = relationship("CheckLog", back_populates="tracking", cascade="all, delete-orphan")


class CheckLog(Base):
    __tablename__ = "check_logs"

    id = Column(Integer, primary_key=True, index=True)
    tracking_id = Column(Integer, ForeignKey("trackings.id"), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    checked_at = Column(DateTime, default=datetime.utcnow)
    is_changed = Column(Boolean, default=False)

    tracking = relationship("Tracking", back_populates="logs")


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    telegram_chat_id = Column(String(100), default="", nullable=True)
    telegram_notifications = Column(Boolean, default=False)
    email_notifications = Column(Boolean, default=False)
    notification_email = Column(String(255), default="", nullable=True)
    smtp_server = Column(String(255), default="smtp.gmail.com", nullable=True)
    smtp_port = Column(Integer, default=587, nullable=True)
    smtp_email = Column(String(255), default="", nullable=True)
    smtp_password = Column(String(255), default="", nullable=True)
    default_check_interval = Column(Integer, default=10)

    user = relationship("User", back_populates="settings")


# Database engine
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    """Создание таблиц в базе данных."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """Dependency для получения сессии БД."""
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
