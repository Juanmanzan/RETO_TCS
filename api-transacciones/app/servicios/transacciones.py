import logging
from time import perf_counter

from app.core.transacciones.ids import (
    generar_trace_id,
    generar_transaccion_id,
)

from app.core.transacciones.montos import (
    convertir_a_centavos,
    convertir_a_decimal,
)

from app.core.transacciones.resultados import (
    interpretar_resultado_redis,
)

from app.esquemas.transacciones import (
    EstadoTransaccion,
    TransferenciaRequest,
    TransferenciaResponse,
)

from app.infraestructura.redis.scripts import (
    ScriptsRedis,
)

from app.infraestructura.observabilidad.metricas import (
    DURACION_REDIS_LUA,
    ERRORES_TRANSACCIONES_TOTAL,
    TRANSACCIONES_TOTAL,
    DURACION_HTTP_TRANSACCION,
)

from app.infraestructura.observabilidad.logging import (
    registrar_evento,
)


logger = logging.getLogger(__name__)


class ServicioTransacciones:

    def __init__(
        self,
        scripts_redis: ScriptsRedis, ## recibe una instancia de ScriptsRedis
    ):
        self.scripts_redis = scripts_redis ## guarda la instancia como atributo interno

    ## procesa la transferencia empleando una instancia de ScriptsRedis
    async def procesar_transancion(
        self,
        transferencia: TransferenciaRequest,
    ) -> TransferenciaResponse:

        inicio_http = perf_counter() ## tiempo de entrada de la peticion http

        # genera un identificador unico para la transaccion
        transaccion_id = generar_transaccion_id()

        # genera el identificador utilizado para seguir la transaccion
        trace_id = generar_trace_id()

        # convierte el monto decimal a centavos para trabajar con redis
        monto_centavos = convertir_a_centavos(
            transferencia.monto
        )

        inicio_lua = perf_counter() ## tiempo antes de entrar a lua

        # ejecuta de forma atomica la transferencia mediante lua en redis
        try:

            resultado_redis = (
                await self.scripts_redis.ejecutar_transancion(
                    cuenta_origen_id=transferencia.cuenta_origen_id,
                    cuenta_destino_id=transferencia.cuenta_destino_id,
                    monto_centavos=monto_centavos,
                    clave_idempotencia=transferencia.clave_idempotencia,
                    transaccion_id=transaccion_id,
                    trace_id=trace_id,
                    moneda=transferencia.moneda,
                    descripcion=transferencia.descripcion,
                )
            )

        except Exception as error:

            duracion_lua_ms = (
                perf_counter() - inicio_lua
            ) * 1000 ## tiempo en que se demoro el procesamiento en lua

            ## registra la cantidad de errores ocurridos durante el procesamiento Redis/Lua
            ERRORES_TRANSACCIONES_TOTAL.labels(
                tipo="redis_lua",
            ).inc()

            ## registra un unico error con el detalle completo de la excepcion
            logger.exception(
                "Error ejecutando transferencia en Redis/Lua "
                "trace_id=%s "
                "transaccion_id=%s "
                "duracion_ms=%.3f "
                "tipo_error=%s "
                "detalle_error=%s",
                trace_id,
                transaccion_id,
                duracion_lua_ms,
                type(error).__name__,
                str(error),
            )

            raise

        duracion_lua_ms = (
            perf_counter() - inicio_lua
        ) * 1000 ## tiempo en que se demoro el procesamiento en lua

        ## registra el tiempo utilizado por Redis/Lua
        DURACION_REDIS_LUA.observe(
            duracion_lua_ms / 1000
        )

        # transforma la respuesta cruda de redis en un resultado del dominio
        resultado = interpretar_resultado_redis(
            resultado_redis
        )

        ## registra la salida exitosa del procesamiento atomico
        ## realizado por Redis/Lua para poder buscar la transaccion
        ## posteriormente usando trace_id o transaccion_id.
        registrar_evento(
            logger,
            "Transaccion finalizada por Redis/Lua",
            componente="api-transacciones",
            evento="redis_lua_finalizado",
            trace_id=trace_id,
            transaccion_id=resultado.transaccion_id,
            estado=resultado.estado,
            motivo=resultado.motivo,
            clave_idempotencia=transferencia.clave_idempotencia,
            duracion_ms=duracion_lua_ms,
        )

        ## cuando la solicitud no es idempotente, Lua tambien
        ## registra el evento dentro de Redis Stream mediante XADD.
        if resultado.tipo_resultado != "IDEMPOTENTE":

            registrar_evento(
                logger,
                "Evento creado en Redis Stream",
                componente="api-transacciones",
                evento="evento_stream_creado",
                trace_id=trace_id,
                transaccion_id=resultado.transaccion_id,
                estado=resultado.estado,
                motivo=resultado.motivo,
                clave_idempotencia=transferencia.clave_idempotencia,
            )

        ## registra una sola vez el resultado final de la transaccion
        TRANSACCIONES_TOTAL.labels(
            estado=resultado.estado,
            motivo=resultado.motivo or "NINGUNO",
        ).inc()

        ## el detalle individual de una transaccion exitosa se mantiene
        ## solamente en DEBUG para evitar generar miles de logs por segundo
        logger.debug(
            "Transferencia procesada por Redis/Lua "
            "trace_id=%s "
            "transaccion_id=%s "
            "estado=%s "
            "motivo=%s "
            "duracion_ms=%.3f",
            trace_id,
            resultado.transaccion_id,
            resultado.estado,
            resultado.motivo,
            duracion_lua_ms,
        )

        ## calcula el tiempo total utilizado por el servicio
        duracion_http = (
            perf_counter() - inicio_http
        )

        ## registra el tiempo total de procesamiento de la peticion
        DURACION_HTTP_TRANSACCION.observe(
            duracion_http
        )

        # construye la respuesta que se enviara al cliente
        return TransferenciaResponse(
            transaccion_id=resultado.transaccion_id,
            estado=EstadoTransaccion(resultado.estado),
            motivo=resultado.motivo,
            cuenta_origen_id=transferencia.cuenta_origen_id,
            cuenta_destino_id=transferencia.cuenta_destino_id,
            monto=convertir_a_decimal(
                monto_centavos
            ),
            moneda=transferencia.moneda,
            descripcion=transferencia.descripcion,
            clave_idempotencia=transferencia.clave_idempotencia

        )
