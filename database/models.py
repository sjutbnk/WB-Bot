from datetime import datetime, time
from sqlalchemy import BigInteger, String, Boolean, DateTime, Time, Integer
from sqlalchemy.orm import Mapped, mapped_column
from database.base import Base

class User(Base):
    """Таблица авторизованных пользователей бота (админов и менеджеров)."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True) # Telegram User ID
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class WBCredentials(Base):
    """Таблица для динамического хранения токенов Wildberries API."""
    __tablename__ = "wb_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    api_token: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    adv_token: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TrackedCompetitor(Base):
    """Таблица артикулов конкурентов для ежедневного парсинга."""
    __tablename__ = "tracked_competitors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_sku: Mapped[str | None] = mapped_column(String(50), nullable=True) # Наш артикул для сравнения
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BotSettings(Base):
    """Настройки времени отправки отчетов по рекламе и поставкам."""
    __tablename__ = "bot_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    
    # Отчет по рекламе и кабинету (ежедневно)
    adv_report_time: Mapped[time] = mapped_column(Time, default=time(9, 0)) # 09:00 по умолчанию
    adv_report_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Отчет по поставкам (раз в неделю)
    supply_report_day: Mapped[int] = mapped_column(Integer, default=0) # 0 = Понедельник, 6 = Воскресенье
    supply_report_time: Mapped[time] = mapped_column(Time, default=time(10, 0)) # 10:00 по умолчанию
    supply_report_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    timezone: Mapped[str] = mapped_column(String(50), default="Europe/Moscow")
