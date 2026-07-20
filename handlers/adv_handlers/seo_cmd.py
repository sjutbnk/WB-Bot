import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from database.requests import get_wb_creds, get_bot_settings
from keyboards.inline import get_seo_menu_markup
from services.wb_client import WBClient
from services.gemini_service import GeminiService
from utils.states import SEOStates
from utils.filters import IsAdminFilter
from utils.formatters import get_header, get_divider

logger = logging.getLogger(__name__)
router = Router()
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())

@router.message(F.text == "✨ SEO и ТЗ")
async def handle_seo_menu(message: Message):
    """Выводит меню работы с SEO и инфографикой."""
    text = (
        f"{get_header('SEO и Инфографика (Gemini)')}"
        f"🤖 Интеграция с искусственным интеллектом Gemini позволяет:\n"
        f" ▫️ **Оптимизировать описание**: автоматически вписать нужные ключевые слова.\n"
        f" ▫️ **Сгенерировать ТЗ для дизайнера**: продумать воронку инфографики на основе карточки.\n\n"
        f"Выберите нужное действие на клавиатуре ниже:"
    )
    await message.answer(text, reply_markup=get_seo_menu_markup())

# --- Ветка SEO-оптимизации ---

@router.callback_query(F.data == "seo_optimize")
async def start_seo_optimize(callback: CallbackQuery, state: FSMContext):
    """Первый шаг: запрос артикула."""
    await callback.message.answer(
        "📝 **Оптимизация описания товара**\n\n"
        "Отправьте мне артикул (SKU) товара на Wildberries, описание которого вы хотите переписать. "
        "Для отмены введите `отмена`."
    )
    await state.set_state(SEOStates.waiting_for_sku)
    await callback.answer()

@router.message(SEOStates.waiting_for_sku)
async def process_seo_sku(message: Message, state: FSMContext):
    """Второй шаг: получение артикула и запрос ключевых слов."""
    sku = message.text.strip()
    if sku.lower() == "отмена":
        await message.answer("❌ Процесс отменен.")
        await state.clear()
        return

    status_msg = await message.answer("⏳ **Поиск товара на Wildberries...**\n[▒░░░░░░░░░] 20%")
    
    creds = await get_wb_creds()
    client = WBClient(api_token=creds.api_token)
    
    # Пытаемся получить карточку
    cards = await client.get_cards()
    card = next((c for c in cards if str(c.get("nmId")) == sku or c.get("vendorCode") == sku), None)
    
    if not card and not client.is_mock:
        # Если реальный API не вернул, попробуем через публичный API получить хотя бы базовую инфу
        public_data = await client.get_competitor_data(sku)
        if public_data:
            card = {
                "nmId": int(sku),
                "title": public_data["name"],
                "description": f"Товар бренда {public_data['brand']}.",
                "characteristics": [{"name": "Бренд", "value": [public_data["brand"]]}]
            }
            
    if not card:
        # Если и там нет, создаем пустышку-заглушку, чтобы процесс не падал
        card = {
            "nmId": int(sku),
            "title": f"Товар {sku}",
            "description": "Описание не найдено на WB. Введите ключи, перепишем с нуля.",
            "characteristics": []
        }

    await state.update_data(card=card)
    await status_msg.delete()
    
    await message.answer(
        f"📦 **Найден товар**: {card.get('title')}\n\n"
        f"Теперь отправьте список **ключевых слов** через запятую, которые нужно встроить в описание.\n"
        f"Пример: `футболка оверсайз, хлопок, летняя одежда`"
    )
    await state.set_state(SEOStates.waiting_for_keywords)

@router.message(SEOStates.waiting_for_keywords)
async def process_seo_keywords(message: Message, state: FSMContext):
    """Третий шаг: отправка промпта в Gemini и вывод результата."""
    keywords_raw = message.text.strip()
    if keywords_raw.lower() == "отмена":
        await message.answer("❌ Процесс отменен.")
        await state.clear()
        return

    keywords = [k.strip() for k in keywords_raw.split(",") if k.strip()]
    data = await state.get_data()
    card = data.get("card")
    
    status_msg = await message.answer("⏳ **Запуск AI-ассистента...**\n[▒░░░░░░░░░] 10%")
    
    # Инициализация Gemini
    settings_rec = await get_bot_settings()
    gemini = GeminiService(api_key=settings_rec.gemini_api_key)
    
    await status_msg.edit_text("⏳ **Gemini анализирует текущую карточку товара...**\n[████░░░░░░] 40%")
    
    title = card.get("title", "")
    description = card.get("description", "")
    characteristics = card.get("characteristics", [])
    
    await status_msg.edit_text("⏳ **Gemini переписывает описание под SEO...**\n[████████░░] 80%")
    
    new_description = await gemini.generate_seo_description(title, description, keywords, characteristics)
    
    await status_msg.delete()
    
    # Отправляем результат
    header = get_header("Результат SEO-Оптимизации")
    await message.answer(f"{header}{new_description}")
    await state.clear()

# --- Ветка ТЗ Инфографики ---

@router.callback_query(F.data == "seo_graphics")
async def start_graphics_brief(callback: CallbackQuery, state: FSMContext):
    """Запрос артикула для генерации ТЗ."""
    await callback.message.answer(
        "🎨 **Генерация ТЗ для дизайнера инфографики**\n\n"
        "Отправьте мне артикул (SKU) товара на Wildberries, для которого нужно спроектировать воронку слайдов. "
        "Для отмены введите `отмена`."
    )
    await state.set_state(SEOStates.waiting_for_graphics_sku)
    await callback.answer()

@router.message(SEOStates.waiting_for_graphics_sku)
async def process_graphics_sku(message: Message, state: FSMContext):
    """Поиск карточки и генерация ТЗ через Gemini."""
    sku = message.text.strip()
    if sku.lower() == "отмена":
        await message.answer("❌ Процесс отменен.")
        await state.clear()
        return

    status_msg = await message.answer("⏳ **Загрузка данных карточки с WB...**\n[▒░░░░░░░░░] 20%")
    
    creds = await get_wb_creds()
    client = WBClient(api_token=creds.api_token)
    
    # Получение карточки
    cards = await client.get_cards()
    card = next((c for c in cards if str(c.get("nmId")) == sku or c.get("vendorCode") == sku), None)
    
    if not card and not client.is_mock:
        public_data = await client.get_competitor_data(sku)
        if public_data:
            card = {
                "nmId": int(sku),
                "title": public_data["name"],
                "description": f"Товар бренда {public_data['brand']}.",
                "characteristics": [{"name": "Бренд", "value": [public_data["brand"]]}]
            }
            
    if not card:
        card = {
            "nmId": int(sku),
            "title": f"Товар {sku}",
            "description": "Описание отсутствует.",
            "characteristics": []
        }

    await status_msg.edit_text("⏳ **Gemini анализирует характеристики и строит воронку слайдов...**\n[██████░░░░] 60%")
    
    settings_rec = await get_bot_settings()
    gemini = GeminiService(api_key=settings_rec.gemini_api_key)
    
    title = card.get("title", "")
    description = card.get("description", "")
    characteristics = card.get("characteristics", [])
    
    brief = await gemini.generate_graphics_brief(title, description, characteristics)
    
    await status_msg.delete()
    
    header = get_header("ТЗ на Инфографику (Gemini)")
    # ТЗ может быть длинным, отправляем целиком
    await message.answer(f"{header}{brief}")
    await state.clear()
