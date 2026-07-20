from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from config.settings import settings
from database.requests import get_user, register_user

class IsAdminFilter(BaseFilter):
    """Фильтр для проверки, является ли пользователь администратором/менеджером."""
    
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user_id = event.from_user.id
        
        # Проверяем, есть ли ID в списке разрешенных из .env
        if user_id in settings.admin_ids:
            # Автоматически регистрируем в БД, если его там еще нет
            username = event.from_user.username
            full_name = event.from_user.full_name
            await register_user(user_id, username, full_name)
            return True
            
        # Если не админ, вежливо отказываем
        if isinstance(event, Message):
            await event.answer("🔒 Доступ ограничен. Вы не авторизованы для использования этого бота.")
        elif isinstance(event, CallbackQuery):
            await event.answer("🔒 Доступ ограничен.", show_alert=True)
            
        return False
