import logging
from aiogram import Router
from utils.filters import IsAdminFilter

logger = logging.getLogger(__name__)
router = Router()
# Применяем фильтр админа ко всем обработчикам роутера
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())
