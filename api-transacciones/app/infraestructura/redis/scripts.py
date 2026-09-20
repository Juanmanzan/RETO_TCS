from pathlib import Path
from redis.asyncio import Redis
from redis.exceptions import NoScriptError
from app.config.settings import settings


# obtiene la ruta del script de transferencia 
RUTA_SCRIPT_TRANSFERENCIA = (
    Path(__file__).resolve().parent
    / "transferencia.lua"
)


class ScriptsRedis:

    ## inicializa la clase cuando se crea una intancia de ella 
    def __init__(self, cliente_redis: Redis):
        self.cliente_redis = cliente_redis
        self.sha_transferencia: str | None = None

    ## carga el script de transferencia en redis y almacena su sha
    async def cargar_script_transferencia(self) -> None:
        ## lee el scrip de lua y lo almacena en contenido_script
        contenido_script = RUTA_SCRIPT_TRANSFERENCIA.read_text(encoding="utf-8")
        ## carga el scrip en redis y genera un hash del scrip 
        self.sha_transferencia = await self.cliente_redis.script_load(
            contenido_script
        )

    ## funcion que se encarga de ejecutar el script de lua 
    async def ejecutar_transancion(
        self,
        cuenta_origen_id: int,
        cuenta_destino_id: int,
        monto_centavos: int,
        clave_idempotencia: str,
        transaccion_id: str,
        trace_id: str,
        moneda: str,
        descripcion: str,
    ):

        ## si no existe un sha del script cargado en redis 
        if not self.sha_transferencia:
            await self.cargar_script_transferencia()

        clave_origen = str(cuenta_origen_id)
        clave_destino = str(cuenta_destino_id)

        clave_idempotencia_redis = (
            f"idempotencia:{clave_idempotencia}"
        )

        try:
            ## ejecuta el script de lua, deacuerdo al script cargado con el hash
            ## pasa las 4 keys necesarias para las consultas dentro del script de lua
            ## pasa los argumentos para las validaciaones dentro de lua 
            return await self.cliente_redis.evalsha(
                self.sha_transferencia,
                4,

                # keys
                clave_origen,
                clave_destino,
                clave_idempotencia_redis,
                settings.redis_stream_transacciones,

                # args
                transaccion_id,
                trace_id,
                monto_centavos,
                moneda,
                descripcion,
                clave_idempotencia,
            )

       ###  redis puede perder el cache de scripts despues de un reinicio por lo que se vuelve a cargar y ejecutar
        except NoScriptError:
      
            await self.cargar_script_transferencia()

            return await self.cliente_redis.evalsha(
                self.sha_transferencia,
                4,

                # keys
                clave_origen,
                clave_destino,
                clave_idempotencia_redis,
                settings.redis_stream_transacciones,

                # args
                transaccion_id,
                trace_id,
                monto_centavos,
                moneda,
                descripcion,
                clave_idempotencia,
            )