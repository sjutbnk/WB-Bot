from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from config.settings import settings

# Инициализируем асинхронный движок SQLAlchemy для работы с PostgreSQL
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# Фабрика асинхронных сессий
async_session = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession
)

class Base(DeclarativeBase):
    pass

async def init_db():
    """Создает таблицы в БД, если они еще не созданы."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
