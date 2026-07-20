from datetime import time
from typing import List, Optional
from sqlalchemy import select, delete
from database.base import async_session
from database.models import User, WBCredentials, TrackedCompetitor, BotSettings
from config.settings import settings

async def init_default_records():
    """Инициализирует записи настроек и токенов по умолчанию, если их еще нет."""
    async with async_session() as session:
        # Инициализация токенов из .env
        creds_query = await session.execute(select(WBCredentials).where(WBCredentials.id == 1))
        creds = creds_query.scalar_one_or_none()
        if not creds:
            # Берем дефолтные значения из настроек среды
            new_creds = WBCredentials(
                id=1,
                api_token=settings.wb_api_token,
                adv_token=settings.wb_adv_token
            )
            session.add(new_creds)

        # Инициализация настроек бота
        settings_query = await session.execute(select(BotSettings).where(BotSettings.id == 1))
        bot_sett = settings_query.scalar_one_or_none()
        if not bot_sett:
            new_settings = BotSettings(
                id=1,
                adv_report_time=time(9, 0),
                supply_report_day=0, # Понедельник
                supply_report_time=time(10, 0),
                timezone="Europe/Moscow"
            )
            session.add(new_settings)
            
        await session.commit()

# --- Пользователи ---

async def get_user(user_id: int) -> Optional[User]:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

async def register_user(user_id: int, username: Optional[str], full_name: Optional[str]) -> User:
    async with async_session() as session:
        db_user = await get_user(user_id)
        if not db_user:
            db_user = User(id=user_id, username=username, full_name=full_name)
            session.add(db_user)
            await session.commit()
            await session.refresh(db_user)
        return db_user

async def get_active_users() -> List[User]:
    async with async_session() as session:
        result = await session.execute(select(User).where(User.is_active == True))
        return list(result.scalars().all())

# --- Токены WB ---

async def get_wb_creds() -> WBCredentials:
    async with async_session() as session:
        result = await session.execute(select(WBCredentials).where(WBCredentials.id == 1))
        creds = result.scalar_one_or_none()
        if not creds:
            # Подстраховка
            creds = WBCredentials(id=1, api_token=settings.wb_api_token, adv_token=settings.wb_adv_token)
            session.add(creds)
            await session.commit()
            await session.refresh(creds)
        return creds

async def update_wb_creds(api_token: Optional[str] = None, adv_token: Optional[str] = None):
    async with async_session() as session:
        result = await session.execute(select(WBCredentials).where(WBCredentials.id == 1))
        creds = result.scalar_one_or_none()
        if creds:
            if api_token is not None:
                creds.api_token = api_token
            if adv_token is not None:
                creds.adv_token = adv_token
            await session.commit()

# --- Настройки бота ---

async def get_bot_settings() -> BotSettings:
    async with async_session() as session:
        result = await session.execute(select(BotSettings).where(BotSettings.id == 1))
        bot_sett = result.scalar_one_or_none()
        if not bot_sett:
            bot_sett = BotSettings(id=1)
            session.add(bot_sett)
            await session.commit()
            await session.refresh(bot_sett)
        return bot_sett

async def update_bot_settings(
    adv_report_time: Optional[time] = None,
    adv_report_enabled: Optional[bool] = None,
    supply_report_day: Optional[int] = None,
    supply_report_time: Optional[time] = None,
    supply_report_enabled: Optional[bool] = None,
    timezone: Optional[str] = None
):
    async with async_session() as session:
        result = await session.execute(select(BotSettings).where(BotSettings.id == 1))
        bot_sett = result.scalar_one_or_none()
        if bot_sett:
            if adv_report_time is not None:
                bot_sett.adv_report_time = adv_report_time
            if adv_report_enabled is not None:
                bot_sett.adv_report_enabled = adv_report_enabled
            if supply_report_day is not None:
                bot_sett.supply_report_day = supply_report_day
            if supply_report_time is not None:
                bot_sett.supply_report_time = supply_report_time
            if supply_report_enabled is not None:
                bot_sett.supply_report_enabled = supply_report_enabled
            if timezone is not None:
                bot_sett.timezone = timezone
            await session.commit()

# --- Конкуренты ---

async def add_competitor(sku: str, name: Optional[str] = None, target_sku: Optional[str] = None) -> bool:
    async with async_session() as session:
        query = await session.execute(select(TrackedCompetitor).where(TrackedCompetitor.sku == sku))
        existing = query.scalar_one_or_none()
        if existing:
            return False  # Уже существует
        
        competitor = TrackedCompetitor(sku=sku, name=name, target_sku=target_sku)
        session.add(competitor)
        await session.commit()
        return True

async def remove_competitor(sku: str) -> bool:
    async with async_session() as session:
        query = await session.execute(select(TrackedCompetitor).where(TrackedCompetitor.sku == sku))
        existing = query.scalar_one_or_none()
        if not existing:
            return False
        
        await session.execute(delete(TrackedCompetitor).where(TrackedCompetitor.sku == sku))
        await session.commit()
        return True

async def get_competitors() -> List[TrackedCompetitor]:
    async with async_session() as session:
        result = await session.execute(select(TrackedCompetitor).order_by(TrackedCompetitor.created_at))
        return list(result.scalars().all())
