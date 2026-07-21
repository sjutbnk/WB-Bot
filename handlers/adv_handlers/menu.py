import logging
import os
from datetime import datetime, time
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, FSInputFile
from database.requests import get_wb_creds, get_bot_settings, update_bot_settings
from keyboards.reply import get_adv_main_menu
from keyboards.inline import get_settings_markup, get_hours_markup
from services.wb_client import WBClient
from services.adv_analyzer import AdvAnalyzer
from services.excel_generator import ExcelGenerator
from utils.filters import IsAdminFilter
from utils.formatters import get_header, get_divider, format_currency, format_percent, format_number
from schedulers.report_scheduler import reschedule_adv_report

logger = logging.getLogger(__name__)
router = Router()
router.message.filter(IsAdminFilter())

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Приветствие и вывод главного меню бота по рекламе."""
    welcome_text = (
        f"👋 **Приветствую, {message.from_user.first_name}!**\n\n"
        f"Я — **Бот по рекламе и аналитике кабинета Wildberries**.\n"
        f"Помогу отслеживать воронку продаж, анализировать расходы на рекламу, "
        f"оптимизировать SEO-карточки (через Gemini) и следить за конкурентами.\n\n"
        f"Используйте кнопки нижнего меню для управления."
    )
    await message.answer(welcome_text, reply_markup=get_adv_main_menu())

@router.message(F.text == "📊 Аналитика")
async def handle_analytics(message: Message):
    """Формирует и присылает отчет по общим продажам и заказам кабинета."""
    # Шаг 1: Анимация начала
    status_msg = await message.answer("⏳ **Запрос данных из Wildberries...**\n[▒░░░░░░░░░] 15%")
    
    creds = await get_wb_creds()
    client = WBClient(api_token=creds.api_token)
    
    # Шаг 2: Получение данных
    await status_msg.edit_text("⏳ **Загрузка заказов и выкупов...**\n[████░░░░░░] 45%")
    orders = await client.get_orders(days_ago=14)
    sales = await client.get_sales(days_ago=14)
    
    # Шаг 3: Обработка данных
    await status_msg.edit_text("⏳ **Анализ воронки и показателей...**\n[████████░░] 80%")
    stats = AdvAnalyzer.analyze_cabinet(orders, sales)
    
    # Шаг 4: Вывод отчета
    report = (
        f"{get_header('Аналитика Кабинета')}"
        f"📅 **Вчера:**\n"
        f" ▫️ Заказы: **{stats['yesterday_orders_count']} шт.** (на {format_currency(stats['yesterday_orders_sum'])})\n"
        f" ▫️ Выкупы: **{stats['yesterday_sales_count']} шт.** (чистая выручка: {format_currency(stats['yesterday_sales_sum'])})\n"
        f"{get_divider()}"
        f"📈 **Воронка кабинета (за 14 дней):**\n"
        f" ▫️ Всего заказов: **{stats['total_orders_count']} шт.**\n"
        f" ▫️ Всего выкупов: **{stats['total_sales_count']} шт.**\n"
        f" ▫️ Процент выкупа: **{format_percent(stats['redemption_rate'])}**\n"
        f" ▫️ Процент возвратов: **{format_percent(stats['return_rate'])}**\n\n"
        f"💡 *Выручка вчера указана 'чистыми' (к перечислению) после вычета комиссии WB.*"
    )
    
    await status_msg.delete()
    await message.answer(report)

@router.message(F.text == "🎯 Реклама")
async def handle_advertising(message: Message):
    """Отчет по воронке рекламных кампаний с генерацией Excel."""
    status_msg = await message.answer("⏳ **Загрузка рекламных кампаний...**\n[▒░░░░░░░░░] 15%")
    
    creds = await get_wb_creds()
    client = WBClient(adv_token=creds.adv_token)
    
    await status_msg.edit_text("⏳ **Получение детальной статистики...**\n[████░░░░░░] 40%")
    campaigns = await client.get_ad_campaigns()
    
    # Отфильтруем только активные кампании (статус 9 - идут показы, или возьмем все активные)
    active_campaigns = [c for c in campaigns if c.get("status") in [9, 11]]
    active_cids = [c["advertId"] for c in active_campaigns]
    
    if not active_cids:
        await status_msg.delete()
        await message.answer("❌ Нет активных или приостановленных рекламных кампаний для анализа.")
        return
        
    await status_msg.edit_text("⏳ **Расчет воронки конверсий и маржинальности...**\n[██████░░░░] 65%")
    stats = await client.get_campaign_full_stats(active_cids)
    
    # Генерируем текстовые рекомендации
    funnel_text, recommendations = AdvAnalyzer.analyze_campaign_funnels(stats)
    
    await status_msg.edit_text("⏳ **Формирование детального Excel-отчета...**\n[████████░░] 85%")
    # Формируем данные для Excel в стиле шаблона
    excel_data = AdvAnalyzer.prepare_campaign_excel_data(active_campaigns, stats)
    filename = "report_campaigns_maria_auto.xlsx"
    ExcelGenerator.generate_campaign_report(excel_data, filename)
    
    await status_msg.edit_text("📤 **Отправка отчета...**\n[██████████] 100%")
    
    report_text = (
        f"{get_header('Рекламные Кампании')}"
        f"📊 **Аналитика кампаний вчера:**\n"
        f" ▫️ Всего кампаний в отчете: **{len(active_cids)}**\n"
        f" ▫️ Активные зоны: Поиск, Полки и каталог\n\n"
        f"📋 **Рекомендации по оптимизации:**\n\n" + 
        "\n\n".join(recommendations)
    )
    
    try:
        excel_file = FSInputFile(filename, filename="Рекламные_кампании_Отчет.xlsx")
        await message.answer_document(
            document=excel_file,
            caption=report_text
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке Excel-отчета РК: {e}")
        await message.answer(report_text)
    finally:
        if os.path.exists(filename):
            os.remove(filename)
        await status_msg.delete()

@router.message(F.text == "⚙️ Настройки")
async def handle_settings(message: Message):
    """Выводит настройки времени отчетов."""
    settings_rec = await get_bot_settings()
    
    text = (
        f"{get_header('Настройки Отчетов')}"
        f"⏰ **Ежедневный отчет по рекламе:**\n"
        f" ▫️ Статус: {'🔔 Включен' if settings_rec.adv_report_enabled else '🔕 Выключен'}\n"
        f" ▫️ Время отправки: **{settings_rec.adv_report_time.strftime('%H:%M')} (МСК)**\n\n"
        f"Используйте кнопку ниже для изменения времени рассылки:"
    )
    await message.answer(text, reply_markup=get_settings_markup())

@router.callback_query(F.data == "set_adv_report_time")
async def select_adv_time(callback: CallbackQuery):
    """Показывает клавиатуру выбора часа отправки отчета рекламы."""
    await callback.message.edit_text(
        "⏰ **Выберите час отправки ежедневного отчета по рекламе (МСК):**",
        reply_markup=get_hours_markup(prefix="set_adv_hour_")
    )
    await callback.answer()

@router.callback_query(F.data.startswith("set_adv_hour_"))
async def process_adv_time(callback: CallbackQuery):
    """Обрабатывает выбор часа и обновляет задачу в планировщике."""
    hour = int(callback.data.replace("set_adv_hour_", ""))
    await update_bot_settings(adv_report_time=time(hour, 0))
    
    # Перепланируем задачу в APScheduler
    await reschedule_adv_report(callback.bot)
    
    await callback.answer("Время ежедневного отчета успешно изменено!", show_alert=True)
    
    # Возвращаемся в меню настроек
    settings_rec = await get_bot_settings()
    
    text = (
        f"{get_header('Настройки Отчетов')}"
        f"⏰ **Ежедневный отчет по рекламе:**\n"
        f" ▫️ Статус: {'🔔 Включен' if settings_rec.adv_report_enabled else '🔕 Выключен'}\n"
        f" ▫️ Время отправки: **{settings_rec.adv_report_time.strftime('%H:%M')} (МСК)**\n\n"
        f"Используйте кнопку ниже для изменения времени рассылки:"
    )
    await callback.message.edit_text(text, reply_markup=get_settings_markup())
