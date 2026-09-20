from redis.asyncio import Redis
from app.config.settings import settings

## crea una conexion hacia el servicio de redis 
def crear_cliente_redis() -> Redis:
    return Redis.from_url(
        settings.redis_url,
        decode_responses=True,
        socket_timeout=None,
    )