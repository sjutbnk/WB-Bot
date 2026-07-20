from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_settings_markup() -> InlineKeyboardMarkup:
    """Клавиатура управления настройками и токенами."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔑 Обновить Стандартный API", callback_data="set_token_api")
    )
    builder.row(
        InlineKeyboardButton(text="🔑 Обновить Рекламный API", callback_data="set_token_adv")
    )
    builder.row(
        InlineKeyboardButton(text="⏰ Время отчета рекламы", callback_data="set_adv_report_time")
    )
    
    return builder.as_markup()

def get_competitor_menu_markup() -> InlineKeyboardMarkup:
    """Клавиатура управления разделом конкурентов."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить конкурента", callback_data="comp_add"),
        InlineKeyboardButton(text="➖ Удалить конкурента", callback_data="comp_remove")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Сравнить цены/остатки", callback_data="comp_compare")
    )
    return builder.as_markup()

def get_seo_menu_markup() -> InlineKeyboardMarkup:
    """Клавиатура раздела SEO и ТЗ."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✍️ Оптимизировать описание (Gemini)", callback_data="seo_optimize")
    )
    builder.row(
        InlineKeyboardButton(text="🎨 Сгенерировать ТЗ инфографики", callback_data="seo_graphics")
    )
    return builder.as_markup()

def get_days_markup() -> InlineKeyboardMarkup:
    """Клавиатура выбора дня недели для рассылки поставок."""
    days = [
        ("Пн", 0), ("Вт", 1), ("Ср", 2), ("Чт", 3),
        ("Пт", 4), ("Сб", 5), ("Вс", 6)
    ]
    builder = InlineKeyboardBuilder()
    for name, val in days:
        builder.add(InlineKeyboardButton(text=name, callback_data=f"set_supply_day_{val}"))
    builder.adjust(4)
    return builder.as_markup()

def get_hours_markup(prefix: str = "set_report_hour_") -> InlineKeyboardMarkup:
    """Клавиатура выбора часа рассылки отчетов."""
    builder = InlineKeyboardBuilder()
    # Выбираем популярные утренние и дневные часы
    hours = [7, 8, 9, 10, 11, 12, 13, 14, 15, 18, 20]
    for h in hours:
        builder.add(InlineKeyboardButton(text=f"{h:02d}:00", callback_data=f"{prefix}{h}"))
    builder.adjust(4)
    return builder.as_markup()
