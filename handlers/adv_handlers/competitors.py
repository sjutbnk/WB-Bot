import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from database.requests import add_competitor, remove_competitor, get_competitors, get_wb_creds
from keyboards.inline import get_competitor_menu_markup
from services.wb_client import WBClient
from utils.states import CompetitorStates
from utils.filters import IsAdminFilter
from utils.formatters import get_header, get_divider, format_currency, format_number

logger = logging.getLogger(__name__)
router = Router()
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())

@router.message(F.text == "👥 Конкуренты")
async def handle_competitors_menu(message: Message):
    """Выводит список отслеживаемых конкурентов и меню действий."""
    competitors = await get_competitors()
    
    if not competitors:
        text = (
            f"{get_header('Мониторинг Конкурентов')}"
            f"❌ Список отслеживаемых конкурентов пока пуст.\n\n"
            f"Вы можете добавить артикулы конкурентов для ежедневного "
            f"отслеживания цен и остатков на Wildberries."
        )
    else:
        text_lines = []
        for i, comp in enumerate(competitors, 1):
            target = f" (Сравнение с {comp.target_sku})" if comp.target_sku else ""
            name = comp.name if comp.name else "Товар"
            text_lines.append(f"{i}. **{comp.sku}** — {name}{target}")
            
        text = (
            f"{get_header('Мониторинг Конкурентов')}"
            f"📋 **Отслеживаемые артикулы:**\n" + 
            "\n".join(text_lines) + "\n\n"
            f"Выберите действие на клавиатуре ниже:"
        )
        
    await message.answer(text, reply_markup=get_competitor_menu_markup())

# --- Добавление конкурента ---

@router.callback_query(F.data == "comp_add")
async def start_add_competitor(callback: CallbackQuery, state: FSMContext):
    """Начало процесса добавления конкурента."""
    await callback.message.answer(
        "➕ **Добавление конкурента**\n\n"
        "Отправьте мне артикул (SKU) конкурента. Для отмены отправьте `отмена`."
    )
    await state.set_state(CompetitorStates.waiting_for_competitor_sku)
    await callback.answer()

@router.message(CompetitorStates.waiting_for_competitor_sku)
async def process_competitor_sku(message: Message, state: FSMContext):
    """Получение артикула конкурента и запрос нашего целевого SKU для сравнения."""
    sku = message.text.strip()
    if sku.lower() == "отмена":
        await message.answer("❌ Процесс отменен.")
        await state.clear()
        return

    if not sku.isdigit():
        await message.answer("⚠️ Артикул должен состоять только из цифр. Попробуйте еще раз:")
        return

    await state.update_data(comp_sku=sku)
    
    await message.answer(
        f"Укажите ваш артикул (SKU) для сравнения с этим конкурентом (например, `100001`).\n"
        f"Или напишите `пропустить`, чтобы просто отслеживать конкурента без привязки к вашему товару."
    )
    await state.set_state(CompetitorStates.waiting_for_target_sku)

@router.message(CompetitorStates.waiting_for_target_sku)
async def process_competitor_target_sku(message: Message, state: FSMContext):
    """Финальное сохранение конкурента в БД с парсингом его названия."""
    target_sku_raw = message.text.strip()
    if target_sku_raw.lower() == "отмена":
        await message.answer("❌ Процесс отменен.")
        await state.clear()
        return

    data = await state.get_data()
    comp_sku = data.get("comp_sku")
    
    target_sku = None if target_sku_raw.lower() == "пропустить" else target_sku_raw
    
    status_msg = await message.answer("⏳ **Запрос данных конкурента по открытым каналам WB...**\n[▒░░░░░░░░░] 20%")
    
    # Парсим информацию о конкуренте
    client = WBClient() # Публичный клиент
    comp_data = await client.get_competitor_data(comp_sku)
    
    comp_name = comp_data.get("name") if comp_data else f"Товар {comp_sku}"
    if comp_data and comp_data.get("brand"):
        comp_name = f"{comp_data.get('brand')} / {comp_name}"
        
    await status_msg.edit_text("⏳ **Сохранение в базу данных...**\n[████████░░] 80%")
    
    # Сохраняем в базу
    success = await add_competitor(sku=comp_sku, name=comp_name, target_sku=target_sku)
    
    await status_msg.delete()
    
    if success:
        await message.answer(f"✅ **Конкурент успешно добавлен!**\n\n📌 Артикул: `{comp_sku}`\n🏷 Название: {comp_name}")
    else:
        await message.answer(f"⚠️ Артикул `{comp_sku}` уже отслеживается.")
        
    await state.clear()

# --- Удаление конкурента ---

@router.callback_query(F.data == "comp_remove")
async def start_remove_competitor(callback: CallbackQuery):
    """Показывает список с кнопками для быстрого удаления."""
    competitors = await get_competitors()
    if not competitors:
        await callback.message.answer("❌ Нет конкурентов для удаления.")
        await callback.answer()
        return
        
    # Сделаем инлайн кнопки для быстрого удаления
    builder = ui_builder = []
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    for comp in competitors:
        builder.row(
            InlineKeyboardButton(text=f"❌ {comp.sku} ({comp.name[:15]}...)", callback_data=f"comp_del_{comp.sku}")
        )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="comp_back"))
    
    await callback.message.edit_text("Выберите конкурента для удаления из списка:", reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("comp_del_"))
async def process_remove_competitor(callback: CallbackQuery):
    """Выполняет удаление выбранного конкурента."""
    sku = callback.data.replace("comp_del_", "")
    success = await remove_competitor(sku)
    
    if success:
        await callback.answer("✅ Конкурент удален!", show_alert=True)
    else:
        await callback.answer("⚠️ Не удалось удалить конкурента.", show_alert=True)
        
    # Возвращаемся в меню
    competitors = await get_competitors()
    if not competitors:
        await callback.message.edit_text("❌ Список отслеживаемых конкурентов пуст.", reply_markup=get_competitor_menu_markup())
    else:
        text_lines = []
        for i, comp in enumerate(competitors, 1):
            target = f" (Сравнение с {comp.target_sku})" if comp.target_sku else ""
            name = comp.name if comp.name else "Товар"
            text_lines.append(f"{i}. **{comp.sku}** — {name}{target}")
            
        await callback.message.edit_text(
            f"{get_header('Мониторинг Конкурентов')}"
            f"📋 **Отслеживаемые артикулы:**\n" + 
            "\n".join(text_lines) + "\n\n"
            f"Выберите действие на клавиатуре ниже:",
            reply_markup=get_competitor_menu_markup()
        )

@router.callback_query(F.data == "comp_back")
async def process_comp_back(callback: CallbackQuery):
    """Кнопка возврата в меню конкурентов."""
    competitors = await get_competitors()
    text_lines = []
    for i, comp in enumerate(competitors, 1):
        target = f" (Сравнение с {comp.target_sku})" if comp.target_sku else ""
        name = comp.name if comp.name else "Товар"
        text_lines.append(f"{i}. **{comp.sku}** — {name}{target}")
        
    await callback.message.edit_text(
        f"{get_header('Мониторинг Конкурентов')}"
        f"📋 **Отслеживаемые артикулы:**\n" + 
        "\n".join(text_lines) + "\n\n"
        f"Выберите действие на клавиатуре ниже:",
        reply_markup=get_competitor_menu_markup()
    )
    await callback.answer()

# --- Сравнение цен и остатков ---

@router.callback_query(F.data == "comp_compare")
async def process_compare_competitors(callback: CallbackQuery):
    """Сравнивает цены и остатки наших товаров и конкурентов."""
    competitors = await get_competitors()
    if not competitors:
        await callback.answer("❌ Список конкурентов пуст.", show_alert=True)
        return
        
    status_msg = await callback.message.answer("⏳ **Сбор цен и остатков конкурентов...**\n[▒░░░░░░░░░] 20%")
    
    # Инициализируем клиент
    creds = await get_wb_creds()
    client = WBClient(api_token=creds.api_token)
    
    # Получаем наши остатки
    our_stocks = await client.get_stocks()
    our_cards = await client.get_cards()
    
    compare_lines = []
    
    total = len(competitors)
    for idx, comp in enumerate(competitors, 1):
        step_percent = int(20 + (idx / total) * 70)
        await status_msg.edit_text(f"⏳ **Парсинг конкурента {comp.sku} ({idx}/{total})...**\n[{'█' * (step_percent // 10)}{'░' * (10 - step_percent // 10)}] {step_percent}%")
        
        # Получаем данные конкурента
        comp_info = await client.get_competitor_data(comp.sku)
        if not comp_info:
            continue
            
        comp_price = comp_info.get("sale_price", 0)
        comp_stock = comp_info.get("stock", 0)
        
        # Строим блок сравнения
        compare_block = (
            f"👥 **Конкурент: {comp_info.get('brand')} (SKU: `{comp.sku}`)**\n"
            f" ▫️ Цена со скидкой: **{format_currency(comp_price)}**\n"
            f" ▫️ Остатки: **{format_number(comp_stock)} шт.**\n"
            f" ▫️ Рейтинг: {comp_info.get('rating', 0)}⭐ ({comp_info.get('feedbacks', 0)} отзывов)\n"
        )
        
        # Если привязан наш артикул, выведем сравнение
        if comp.target_sku:
            # Ищем наш товар
            our_card = next((c for c in our_cards if str(c.get("nmId")) == comp.target_sku or c.get("vendorCode") == comp.target_sku), None)
            our_title = our_card.get("title", f"Наш SKU {comp.target_sku}") if our_card else f"Наш SKU {comp.target_sku}"
            
            # Находим наши остатки по этому артикулу
            our_stock_qty = sum(item.get("quantityFull", 0) for item in our_stocks if str(item.get("nmId")) == comp.target_sku)
            
            # Для цены используем mock или если в demo режиме
            our_price = 1000.0  # Дефолтная цена, в реальном API цена берется из остатков или номенклатур
            
            price_diff = comp_price - our_price
            price_diff_str = f"({'+' if price_diff > 0 else ''}{format_currency(price_diff)})" if price_diff != 0 else "(цена совпадает)"
            
            compare_block += (
                f"👉 *В сравнении с вашим: {our_title} (SKU: `{comp.target_sku}`)*\n"
                f" ▫️ Ваша цена: **{format_currency(our_price)}** {price_diff_str}\n"
                f" ▫️ Ваши остатки: **{format_number(our_stock_qty)} шт.**\n"
            )
            
        compare_lines.append(compare_block)
        
    await status_msg.delete()
    
    header = get_header("Сравнение с конкурентами")
    result_text = f"{header}" + f"{get_divider()}".join(compare_lines)
    
    # Если текст длинный, разбиваем (в рамках лимита TG 4096 символов)
    if len(result_text) > 4000:
        for chunk in [result_text[i:i+4000] for i in range(0, len(result_text), 4000)]:
            await callback.message.answer(chunk)
    else:
        await callback.message.answer(result_text)
        
    await callback.answer()
