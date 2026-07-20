import os
from typing import List
from dotenv import load_dotenv
from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Загружаем .env файл при наличии
load_dotenv()

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Токены Telegram-ботов
    bot_token_adv: str = Field(..., validation_alias="BOT_TOKEN_ADV")
    bot_token_supply: str = Field(..., validation_alias="BOT_TOKEN_SUPPLY")

    # Токены Wildberries API
    wb_api_token: str = Field(..., validation_alias="WB_API_TOKEN")
    wb_adv_token: str = Field(..., validation_alias="WB_ADV_TOKEN")

    # Ключ Gemini API
    gemini_api_key: str = Field(..., validation_alias="GEMINI_API_KEY")

    # Настройки PostgreSQL
    db_user: str = Field("postgres", validation_alias="DB_USER")
    db_password: str = Field("postgres_password", validation_alias="DB_PASSWORD")
    db_host: str = Field("localhost", validation_alias="DB_HOST")
    db_port: int = Field(5432, validation_alias="DB_PORT")
    db_name: str = Field("maria_auto_db", validation_alias="DB_NAME")

    # Администраторы (пользователи с доступом к боту)
    admin_ids_raw: str = Field(..., validation_alias="ADMIN_IDS")

    @computed_field
    @property
    def admin_ids(self) -> List[int]:
        try:
            return [int(x.strip()) for x in self.admin_ids_raw.split(",") if x.strip()]
        except ValueError:
            return []

    @computed_field
    @property
    def database_url(self) -> str:
        host = self.db_host
        # Если бот запущен внутри Docker-контейнера, а хост указан как localhost/127.0.0.1,
        # автоматически перенаправляем на имя сервиса БД "db", описанного в docker-compose.yml
        if (os.path.exists("/.dockerenv") or os.environ.get("IS_DOCKER") == "true") and host in ("localhost", "127.0.0.1"):
            host = "db"
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{host}:{self.db_port}/{self.db_name}"

settings = Settings()
