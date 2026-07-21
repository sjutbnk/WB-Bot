from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

def get_adv_main_menu() -> ReplyKeyboardMarkup:
    """Главное меню для Бота по рекламе."""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📊 Аналитика"),
        KeyboardButton(text="🎯 Реклама")
    )
    builder.row(
        KeyboardButton(text="✨ SEO и ТЗ"),
        KeyboardButton(text="👥 Конкуренты")
    )
    builder.row(
        KeyboardButton(text="⚙️ Настройки")
    )
    
    markup = builder.as_markup()
    markup.resize_keyboard = True
    markup.input_field_placeholder = "Выберите действие..."
    return markup

def get_supply_main_menu() -> ReplyKeyboardMarkup:
    """Главное меню для Бота по поставкам."""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📦 Расчет поставок")
    )
    builder.row(
        KeyboardButton(text="📅 Настройка рассылки")
    )
    
    markup = builder.as_markup()
    markup.resize_keyboard = True
    markup.input_field_placeholder = "Выберите действие..."
    return markup
