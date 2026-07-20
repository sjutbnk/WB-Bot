import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from database.requests import update_wb_creds, get_wb_creds
from utils.states import GeneralStates
from utils.filters import IsAdminFilter
from utils.formatters import get_header, get_divider
from services.wb_client import WBClient

logger = logging.getLogger(__name__)
router = Router()
# Применяем фильтр админа ко всем обработчикам роутера
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())

@router.callback_query(F.data == "set_token_api")
async def start_api_token_update(callback: CallbackQuery, state: FSMContext):
    """Начало процесса обновления стандартного токена API."""
    await callback.message.answer(
        "🔑 **Обновление стандартного токена API Wildberries**\n\n"
        "Отправьте мне новый стандартный токен (Content, Statistics). "
        "Для отмены отправьте слово `отмена`."
    )
    await state.set_state(GeneralStates.waiting_for_api_token)
    await callback.answer()

@router.callback_query(F.data == "set_token_adv")
async def start_adv_token_update(callback: CallbackQuery, state: FSMContext):
    """Начало процесса обновления рекламного токена API."""
    await callback.message.answer(
        "🔑 **Обновление рекламного токена API Wildberries**\n\n"
        "Отправьте мне новый токен продвижения (Продвижение / Реклама). "
        "Для отмены отправьте слово `отмена`."
    )
    await state.set_state(GeneralStates.waiting_for_adv_token)
    await callback.answer()

@router.message(GeneralStates.waiting_for_api_token)
async def process_api_token(message: Message, state: FSMContext):
    """Сохранение нового стандартного токена."""
    token = message.text.strip()
    if token.lower() == "отмена":
        await message.answer("❌ Обновление отменено.")
        await state.clear()
        return

    # Показываем стильную анимацию ожидания
    status_msg = await message.answer("⏳ **Проверка токена...**\n[▒░░░░░░░░░] 10%")
    
    # Проверяем токен, делая легкий запрос остатков
    try:
        await status_msg.edit_text("⏳ **Проверка токена...**\n[████░░░░░░] 40% (Запрос к WB API)")
        client = WBClient(api_token=token)
        
        # Если это тестовый/заглушечный токен, пропускаем
        if client.is_mock:
            await update_wb_creds(api_token=token)
            await status_msg.edit_text("✅ **Стандартный токен сохранен в демо-режиме!**")
        else:
            stocks = await client.get_stocks()
            await status_msg.edit_text("⏳ **Проверка токена...**\n[████████░░] 80% (Валидация данных)")
            
            # Сохраняем в БД
            await update_wb_creds(api_token=token)
            await status_msg.edit_text("✅ **Стандартный токен успешно сохранен и протестирован!**")
    except Exception as e:
        logger.error(f"Ошибка валидации токена: {e}")
        # Всё равно сохраняем на случай временных сбоев API, но предупреждаем
        await update_wb_creds(api_token=token)
        await status_msg.edit_text("⚠️ **Токен сохранен, но не прошел тест связи с WB.**\nВозможно, временный сбой API.")
        
    await state.clear()

@router.message(GeneralStates.waiting_for_adv_token)
async def process_adv_token(message: Message, state: FSMContext):
    """Сохранение нового рекламного токена."""
    token = message.text.strip()
    if token.lower() == "отмена":
        await message.answer("❌ Обновление отменено.")
        await state.clear()
        return

    status_msg = await message.answer("⏳ **Проверка токена продвижения...**\n[▒░░░░░░░░░] 10%")
    
    try:
        await status_msg.edit_text("⏳ **Проверка токена продвижения...**\n[████░░░░░░] 40% (Запрос к WB Рекламе)")
        client = WBClient(adv_token=token)
        
        if client.is_mock:
            await update_wb_creds(adv_token=token)
            await status_msg.edit_text("✅ **Рекламный токен сохранен в демо-режиме!**")
        else:
            campaigns = await client.get_ad_campaigns()
            await status_msg.edit_text("⏳ **Проверка токена продвижения...**\n[████████░░] 80% (Валидация данных)")
            
            await update_wb_creds(adv_token=token)
            await status_msg.edit_text("✅ **Рекламный токен успешно сохранен и протестирован!**")
    except Exception as e:
        logger.error(f"Ошибка валидации рекламного токена: {e}")
        await update_wb_creds(adv_token=token)
        await status_msg.edit_text("⚠️ **Рекламный токен сохранен, но не прошел тест связи.**\nПроверьте права токена.")
        
    await state.clear()
