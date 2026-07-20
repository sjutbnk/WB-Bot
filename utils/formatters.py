from typing import Union

def format_currency(value: Union[int, float]) -> str:
    """Форматирует число в валюту: 15200 -> 15 200 ₽."""
    try:
        return f"{int(value):,} ₽".replace(",", " ")
    except (ValueError, TypeError):
        return "0 ₽"

def format_percent(value: Union[int, float]) -> str:
    """Форматирует число в процент: 4.542 -> 4.54%."""
    try:
        return f"{float(value):.2f}%"
    except (ValueError, TypeError):
        return "0.00%"

def format_number(value: Union[int, float]) -> str:
    """Форматирует обычное число с разделителем тысяч: 1250 -> 1 250."""
    try:
        return f"{int(value):,}".replace(",", " ")
    except (ValueError, TypeError):
        return "0"

def get_progress_bar(percent: float, length: int = 10) -> str:
    """Создает минималистичную шкалу загрузки."""
    percent = max(0.0, min(100.0, percent))
    filled_len = int(round(length * percent / 100))
    bar = "█" * filled_len + "░" * (length - filled_len)
    return f"[{bar}] {percent:.0f}%"

def get_header(title: str) -> str:
    """Создает стильный минималистичный заголовок."""
    line = "─" * 26
    return f"⚡ **{title.upper()}**\n{line}\n"

def get_divider() -> str:
    """Возвращает тонкий разделитель."""
    return "\n" + "─" * 26 + "\n"
