from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config.settings import settings


## funcion que permite crear conexiones hacia postgret
def crear_motor_postgresql() -> AsyncEngine:

    return create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        pool_timeout=5,
        pool_recycle=1800,
    )


motor_postgresql = crear_motor_postgresql()


## permite crear sesiones asincronas para consultar y guardar
## la respuesta generada por la ia
SesionPostgresql = async_sessionmaker(
    bind=motor_postgresql,
    class_=AsyncSession,
    expire_on_commit=False,
)
