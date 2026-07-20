import logging
import os
from datetime import datetime, time
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from aiogram.types import FSInputFile
from database.requests import get_bot_settings, get_active_users, get_wb_creds
from services.wb_client import WBClient
from services.adv_analyzer import AdvAnalyzer
from services.supply_analyzer import SupplyAnalyzer
from services.excel_generator import ExcelGenerator
from utils.formatters import get_header, get_divider, format_currency, format_percent, format_number

logger = logging.getLogger(__name__)

# Глобальные инстансы планировщиков
adv_scheduler: Optional[AsyncIOScheduler] = None
supply_scheduler: Optional[AsyncIOScheduler] = None

# --- Задачи планировщика ---

async def send_daily_adv_report(bot: Bot):
    """Задача автоматической отправки ежедневного отчета по рекламе всем админам."""
    logger.info("Запуск автоматического отчета по рекламе...")
    settings_rec = await get_bot_settings()
    if not settings_rec.adv_report_enabled:
        logger.info("Отчет по рекламе отключен в настройках.")
        return

    users = await get_active_users()
    if not users:
        logger.info("Нет активных пользователей для рассылки.")
        return

    creds = await get_wb_creds()
    client = WBClient(api_token=creds.api_token, adv_token=creds.adv_token)

    # Собираем данные
    orders = await client.get_orders(days_ago=14)
    sales = await client.get_sales(days_ago=14)
    campaigns = await client.get_ad_campaigns()
    
    active_cids = [c["advertId"] for c in campaigns if c.get("status") in [9, 11]]
    
    stats_cabinet = AdvAnalyzer.analyze_cabinet(orders, sales)
    
    if active_cids:
        stats_ads = await client.get_campaign_full_stats(active_cids)
        funnel_text, recommendations = AdvAnalyzer.analyze_campaign_funnels(stats_ads)
    else:
        funnel_text = "Нет активных рекламных кампаний для анализа."
        recommendations = ["Запустите рекламу на WB для анализа."]

    report_text = (
        f"📅 **ЕЖЕДНЕВНЫЙ АВТО-ОТЧЕТ РЕКЛАМЫ (МСК)**\n"
        f"{get_divider()}"
        f"📊 **Аналитика Кабинета вчера:**\n"
        f" ▫️ Заказы: **{stats_cabinet['yesterday_orders_count']} шт.** (на {format_currency(stats_cabinet['yesterday_orders_sum'])})\n"
        f" ▫️ Выкупы: **{stats_cabinet['yesterday_sales_count']} шт.** ({format_currency(stats_cabinet['yesterday_sales_sum'])})\n"
        f" ▫️ Выкуп: **{format_percent(stats_cabinet['redemption_rate'])}** | Возвраты: **{format_percent(stats_cabinet['return_rate'])}**\n"
        f"{get_divider()}"
        f"🎯 **Рекламные кампании:**\n{funnel_text}\n"
        f"{get_divider()}"
        f"💡 **Рекомендации:**\n" + "\n\n".join(recommendations)
    )

    # Рассылаем всем админам
    for u in users:
        try:
            await bot.send_message(chat_id=u.id, text=report_text)
            logger.info(f"Отчет успешно отправлен пользователю {u.id}")
        except Exception as e:
            logger.error(f"Не удалось отправить отчет пользователю {u.id}: {e}")


async def send_weekly_supply_report(bot: Bot):
    """Задача автоматической отправки еженедельного Excel отчета по поставкам всем админам."""
    logger.info("Запуск автоматического расчета поставок...")
    settings_rec = await get_bot_settings()
    if not settings_rec.supply_report_enabled:
        logger.info("Отчет по поставкам отключен в настройках.")
        return

    users = await get_active_users()
    if not users:
        return

    creds = await get_wb_creds()
    client = WBClient(api_token=creds.api_token)

    stocks = await client.get_stocks()
    sales = await client.get_sales(days_ago=30)
    supply_data = SupplyAnalyzer.calculate_supplies(stocks, sales, target_days=30)

    filename = "auto_report_supply.xlsx"
    ExcelGenerator.generate_supply_report(supply_data, filename)

    try:
        excel_file = FSInputFile(filename, filename="Потребность_в_поставках_Авто.xlsx")
        for u in users:
            try:
                await bot.send_document(
                    chat_id=u.id,
                    document=excel_file,
                    caption=(
                        f"📅 **ЕЖЕНЕДЕЛЬНЫЙ АВТО-ОТЧЕТ ПО ПОСТАВКАМ**\n\n"
                        f"В прикрепленном Excel-файле сформированы рекомендации по поставкам и "
                        f"региональному распределению на основе скорости продаж за последние 30 дней."
                    )
                )
                logger.info(f"Отчет поставок отправлен пользователю {u.id}")
            except Exception as e:
                logger.error(f"Ошибка отправки файла пользователю {u.id}: {e}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

# --- Инициализация и динамическое управление расписанием ---

async def start_adv_scheduler(bot: Bot):
    """Запуск планировщика для Бота по рекламе."""
    global adv_scheduler
    if adv_scheduler is not None:
        return

    settings_rec = await get_bot_settings()
    adv_scheduler = AsyncIOScheduler(timezone=settings_rec.timezone)
    
    # Добавляем задачу
    adv_scheduler.add_job(
        send_daily_adv_report,
        trigger="cron",
        hour=settings_rec.adv_report_time.hour,
        minute=settings_rec.adv_report_time.minute,
        id="daily_adv_report",
        args=[bot]
    )
    
    adv_scheduler.start()
    logger.info(f"Планировщик рекламы запущен. Время: {settings_rec.adv_report_time.strftime('%H:%M')} (МСК)")

async def reschedule_adv_report(bot: Bot):
    """Обновляет время запуска ежедневного отчета рекламы из БД."""
    global adv_scheduler
    if adv_scheduler is None:
        return
        
    settings_rec = await get_bot_settings()
    try:
        adv_scheduler.remove_job("daily_adv_report")
    except Exception:
        pass
        
    adv_scheduler.add_job(
        send_daily_adv_report,
        trigger="cron",
        hour=settings_rec.adv_report_time.hour,
        minute=settings_rec.adv_report_time.minute,
        id="daily_adv_report",
        args=[bot]
    )
    logger.info(f"Задача рекламы перепланирована на: {settings_rec.adv_report_time.strftime('%H:%M')}")


async def start_supply_scheduler(bot: Bot):
    """Запуск планировщика для Бота по поставкам."""
    global supply_scheduler
    if supply_scheduler is not None:
        return

    settings_rec = await get_bot_settings()
    supply_scheduler = AsyncIOScheduler(timezone=settings_rec.timezone)
    
    # Добавляем задачу
    # В APScheduler day_of_week принимает: 0-6 (0=Пн), либо 'mon', 'tue' и т.д.
    supply_scheduler.add_job(
        send_weekly_supply_report,
        trigger="cron",
        day_of_week=settings_rec.supply_report_day,
        hour=settings_rec.supply_report_time.hour,
        minute=settings_rec.supply_report_time.minute,
        id="weekly_supply_report",
        args=[bot]
    )
    
    supply_scheduler.start()
    logger.info(f"Планировщик поставок запущен. День: {settings_rec.supply_report_day}, Время: {settings_rec.supply_report_time.strftime('%H:%M')}")

async def reschedule_supply_report(bot: Bot):
    """Обновляет время и день запуска еженедельного отчета поставок из БД."""
    global supply_scheduler
    if supply_scheduler is None:
        return
        
    settings_rec = await get_bot_settings()
    try:
        supply_scheduler.remove_job("weekly_supply_report")
    except Exception:
        pass
        
    supply_scheduler.add_job(
        send_weekly_supply_report,
        trigger="cron",
        day_of_week=settings_rec.supply_report_day,
        hour=settings_rec.supply_report_time.hour,
        minute=settings_rec.supply_report_time.minute,
        id="weekly_supply_report",
        args=[bot]
    )
    logger.info(f"Задача поставок перепланирована на день {settings_rec.supply_report_day}, время {settings_rec.supply_report_time.strftime('%H:%M')}")
