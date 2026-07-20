from aiogram.fsm.state import State, StatesGroup

class GeneralStates(StatesGroup):
    """Общие состояния для обоих ботов."""
    waiting_for_api_token = State()
    waiting_for_adv_token = State()

class SEOStates(StatesGroup):
    """Состояния для SEO и ТЗ в Боте по рекламе."""
    waiting_for_sku = State()
    waiting_for_keywords = State()
    waiting_for_graphics_sku = State()

class CompetitorStates(StatesGroup):
    """Состояния для добавления конкурентов."""
    waiting_for_competitor_sku = State()
    waiting_for_target_sku = State()

class SupplyStates(StatesGroup):
    """Состояния для настроек расписания Бота по поставкам."""
    waiting_for_report_time = State()
