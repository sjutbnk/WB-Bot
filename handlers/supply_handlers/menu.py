import logging
import os
from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, FSInputFile
from database.requests import get_wb_creds, get_bot_settings, update_bot_settings
from keyboards.reply import get_supply_main_menu
from keyboards.inline import get_settings_markup, get_days_markup, get_hours_markup
from services.wb_client import WBClient
from services.supply_analyzer import SupplyAnalyzer
from services.excel_generator import ExcelGenerator
from utils.filters import IsAdminFilter
from utils.formatters import get_header, get_divider
from schedulers.report_scheduler import reschedule_supply_report

logger = logging.getLogger(__name__)
router = Router()
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Приветствие и вывод главного меню бота по поставкам."""
    welcome_text = (
        f"👋 **Приветствую, {message.from_user.first_name}!**\n\n"
        f"Я — **Бот планирования поставок Wildberries**.\n"
        f"Моя главная задача — помогать вам вовремя пополнять склады, "
        f"чтобы карточки товаров не просаживались в позициях из-за отсутствия остатков (Out of Stock).\n\n"
        f"Я рассчитываю скорость продаж, оборачиваемость и строю распределение "
        f"поставок по региональным хабам WB в Excel.\n\n"
        f"Используйте кнопки нижнего меню для взаимодействия."
    )
    await message.answer(welcome_text, reply_markup=get_supply_main_menu())

# --- Ручной запуск расчета поставок ---

@router.message(F.text == "📦 Расчет поставок")
async def handle_supply_calculation(message: Message):
    """Рассчитывает потребность и отправляет Excel-отчет."""
    status_msg = await message.answer("⏳ **Запрос остатков из Wildberries...**\n[▒░░░░░░░░░] 15%")
    
    creds = await get_wb_creds()
    client = WBClient(api_token=creds.api_token)
    
    # Шаг 1: Загрузка остатков
    stocks = await client.get_stocks()
    
    await status_msg.edit_text("⏳ **Загрузка статистики продаж (за 30 дней)...**\n[████░░░░░░] 40%")
    # Загружаем продажи за 30 дней
    sales = await client.get_sales(days_ago=30)
    
    await status_msg.edit_text("⏳ **Анализ региональной оборачиваемости...**\n[██████░░░░] 65%")
    # Вычисляем потребность
    supply_data = SupplyAnalyzer.calculate_supplies(stocks, sales, target_days=30)
    
    await status_msg.edit_text("⏳ **Формирование Excel отчета...**\n[████████░░] 85%")
    # Генерируем Excel
    filename = "report_supply_maria_auto.xlsx"
    ExcelGenerator.generate_supply_report(supply_data, filename)
    
    await status_msg.edit_text("📤 **Отправка документа...**\n[██████████] 100%")
    
    try:
        excel_file = FSInputFile(filename, filename="Потребность_в_поставках.xlsx")
        await message.answer_document(
            document=excel_file,
            caption=(
                f"📦 **Отчет по потребности в поставках готов!**\n\n"
                f"📊 Внутри:\n"
                f" ▫️ Анализ остатков и товаров в пути\n"
                f" ▫️ Скорость продаж (за 14 и 30 дней)\n"
                f" ▫️ Расчет потребности на 30 дней\n"
                f" ▫️ Распределение по 5 региональным складам\n\n"
                f"*Строки с товарами, требующими поставки, подсвечены зеленым цветом.*"
            )
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке файла: {e}")
        await message.answer("❌ Произошла ошибка при отправке файла отчета.")
    finally:
        # Удаляем временный файл
        if os.path.exists(filename):
            os.remove(filename)
        await status_msg.delete()

# --- Раздел Настройки рассылки ---

@router.message(F.text == "📅 Настройка рассылки")
async def handle_schedule_menu(message: Message):
    """Выводит настройки автоматического еженедельного отчета."""
    settings_rec = await get_bot_settings()
    
    days_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    day_name = days_names[settings_rec.supply_report_day]
    time_str = settings_rec.supply_report_time.strftime("%H:%M")
    
    text = (
        f"{get_header('Расписание Отчетов')}"
        f"📅 **Еженедельный отчет по поставкам:**\n"
        f" ▫️ Статус: {'🔔 Активен' if settings_rec.supply_report_enabled else '🔕 Отключен'}\n"
        f" ▫️ День недели: **{day_name}**\n"
        f" ▫️ Время отправки: **{time_str} (МСК)**\n\n"
        f"Выберите параметр для изменения рассылки:"
    )
    
    # Кнопки для настройки расписания
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 Изменить день недели", callback_data="set_day"),
        InlineKeyboardButton(text="⏰ Изменить время", callback_data="set_time")
    )
    builder.row(
        InlineKeyboardButton(
            text="🔕 Отключить рассылку" if settings_rec.supply_report_enabled else "🔔 Включить рассылку",
            callback_data="toggle_supply_report"
        )
    )
    
    await message.answer(text, reply_markup=builder.as_markup())

@router.callback_query(F.data == "toggle_supply_report")
async def toggle_supply_report(callback: CallbackQuery):
    """Включает или выключает еженедельную рассылку отчетов по поставкам."""
    settings_rec = await get_bot_settings()
    new_state = not settings_rec.supply_report_enabled
    await update_bot_settings(supply_report_enabled=new_state)
    
    # Перепланируем рассылку в APScheduler
    await reschedule_supply_report(callback.bot)
    
    # Обновляем сообщение меню
    await callback.answer("Статус рассылки изменен", show_alert=True)
    
    # Имитируем повторный вывод меню с измененным состоянием
    settings_rec = await get_bot_settings()
    days_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    day_name = days_names[settings_rec.supply_report_day]
    time_str = settings_rec.supply_report_time.strftime("%H:%M")
    
    text = (
        f"{get_header('Расписание Отчетов')}"
        f"📅 **Еженедельный отчет по поставкам:**\n"
        f" ▫️ Статус: {'🔔 Активен' if settings_rec.supply_report_enabled else '🔕 Отключен'}\n"
        f" ▫️ День недели: **{day_name}**\n"
        f" ▫️ Время отправки: **{time_str} (МСК)**\n\n"
        f"Выберите параметр для изменения рассылки:"
    )
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    from aiogram.types import InlineKeyboardButton
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 Изменить день недели", callback_data="set_day"),
        InlineKeyboardButton(text="⏰ Изменить время", callback_data="set_time")
    )
    builder.row(
        InlineKeyboardButton(
            text="🔕 Отключить рассылку" if settings_rec.supply_report_enabled else "🔔 Включить рассылку",
            callback_data="toggle_supply_report"
        )
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())

@router.callback_query(F.data == "set_day")
async def select_day_schedule(callback: CallbackQuery):
    """Выводит клавиатуру дней недели."""
    await callback.message.edit_text(
        "📅 **Выберите день недели для автоматической отправки Excel-отчета по поставкам:**",
        reply_markup=get_days_markup()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("set_supply_day_"))
async def process_day_schedule(callback: CallbackQuery):
    """Обрабатывает выбор дня недели."""
    day = int(callback.data.replace("set_supply_day_", ""))
    await update_bot_settings(supply_report_day=day)
    
    # Перепланируем рассылку в APScheduler
    await reschedule_supply_report(callback.bot)
    
    await callback.answer("День недели успешно изменен!", show_alert=True)
    # Возвращаемся в меню настроек
    # Создаем фиктивное сообщение, чтобы вызвать хендлер
    class FakeMessage:
        def __init__(self, msg: Message):
            self.message = msg
            self.from_user = msg.from_user
        async def answer(self, text, reply_markup=None):
            await self.message.edit_text(text, reply_markup=reply_markup)
            
    await handle_schedule_menu(callback.message)

@router.callback_query(F.data == "set_time")
async def select_time_schedule(callback: CallbackQuery):
    """Выводит клавиатуру часов."""
    await callback.message.edit_text(
        "⏰ **Выберите час отправки еженедельного отчета (по Московскому времени):**",
        reply_markup=get_hours_markup()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("set_report_hour_"))
async def process_time_schedule(callback: CallbackQuery):
    """Обрабатывает выбор часа для отчета."""
    from datetime import time
    hour = int(callback.data.replace("set_report_hour_", ""))
    await update_bot_settings(supply_report_time=time(hour, 0))
    
    # Перепланируем рассылку в APScheduler
    await reschedule_supply_report(callback.bot)
    
    await callback.answer("Время отправки изменено!", show_alert=True)
    await handle_schedule_menu(callback.message)


