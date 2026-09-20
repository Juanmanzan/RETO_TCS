import asyncio
import json
import logging
import uuid
from time import perf_counter

from prometheus_client import start_http_server

from redis.exceptions import (
    RedisError,
    ResponseError,
)

from app.config.settings import settings

from app.infraestructura.mensajeria.conexion import (
    crear_cliente_mqtt,
)

from app.infraestructura.redis.conexion import (
    crear_cliente_redis,
)

from app.infraestructura.observabilidad.logging import (
    configurar_logging,
    registrar_evento,
)

from app.infraestructura.observabilidad.metricas import (
    DURACION_PUBLICACION_MQTT,
    ERRORES_MQTT_TOTAL,
    EVENTOS_MQTT_PUBLICADOS_TOTAL,
    EVENTOS_STREAM_RECIBIDOS_TOTAL,
)


logger = logging.getLogger(__name__)


# Genera un ID único cada vez que el script se ejecuta
# Ejemplo de resultado: "worker-a1b2c3d4"
CONSUMIDOR_ID = f"worker-{uuid.uuid4().hex[:8]}"


## cantidad maxima de eventos recuperados/procesados por bloque
TAMANIO_LOTE_STREAM = 100


## tiempo minimo que un mensaje debe permanecer pendiente
## antes de poder ser reclamado por otro consumidor
TIEMPO_MINIMO_PENDING_MS = 5000


## tiempo utilizado antes de volver a intentar una conexion MQTT
TIEMPO_REINTENTO_MQTT_SEGUNDOS = 1


## funcion que crea los consumer group
## comienza a leer todos los mensajes desde el inicio
## cuando detecta una exepcion del tipo BUSYGROUP la ignora
async def crear_grupo_consumidores(
    cliente_redis,
) -> None:

    try:

        await cliente_redis.xgroup_create(
            name=settings.redis_stream_transacciones,
            groupname=settings.redis_consumer_group_mqtt,
            id="0",
            mkstream=True,
        )

    except ResponseError as error:

        if "BUSYGROUP" not in str(error):
            raise


## funcion que se encarga de publicar un evento en mqtt
async def publicar_evento_mqtt(
    cliente_mqtt,
    evento: dict,
) -> None:

    """ campos entregados para el evento

        identificador del mensaje
        "transaccion_id"
        "trace_id"
        "cuenta_origen_id"
        "cuenta_destino_id"
        "monto"
        "moneda"
        "descripcion"
        "estado"
        "motivo"
    """

    ## genera un json a partir de un evento para su consumo
    ## por la API de IA o para la persistencia de los datos en SQL
    mensaje = json.dumps(
        evento,
        ensure_ascii=False,
    )

    inicio_persistencia = perf_counter()

    try:

        ## publica el evento en mqtt para el grupo de persistencia
        await cliente_mqtt.publish(
            settings.mqtt_topic_persistencia,
            payload=mensaje,
            qos=1, ## garantiza que llegue el mensaje al menos una vez
        )

    except Exception:

        ## registra solamente la metrica.
        ## el error completo se registra en procesar_evento
        ## para evitar generar varios logs para el mismo error
        ERRORES_MQTT_TOTAL.labels(
            destino="persistencia",
        ).inc()

        raise

    ## registra cuanto se demoro la publicacion hacia persistencia
    DURACION_PUBLICACION_MQTT.labels(
        destino="persistencia",
    ).observe(
        perf_counter() - inicio_persistencia
    )

    ## registra la cantidad de eventos publicados correctamente
    EVENTOS_MQTT_PUBLICADOS_TOTAL.labels(
        destino="persistencia",
    ).inc()

    ## registra la publicacion exitosa hacia persistencia
    ## para poder seguir la transaccion por trace_id.
    registrar_evento(
        logger,
        "Evento publicado hacia persistencia",
        componente="worker-publicador",
        evento="mqtt_persistencia_publicado",
        trace_id=evento.get(
            "trace_id"
        ),
        transaccion_id=evento.get(
            "transaccion_id"
        ),
        estado=evento.get(
            "estado"
        ),
        motivo=evento.get(
            "motivo"
        ),
        clave_idempotencia=evento.get(
            "clave_idempotencia"
        ),
        nivel=logging.DEBUG,
    )


    inicio_ia = perf_counter()

    try:

        ## publica el evento en mqtt para el grupo de IA
        await cliente_mqtt.publish(
            settings.mqtt_topic_ia,
            payload=mensaje,
            qos=1,
        )

    except Exception:

        ## registra solamente la metrica.
        ## el error completo se registra en procesar_evento
        ERRORES_MQTT_TOTAL.labels(
            destino="ia",
        ).inc()

        raise

    ## registra cuanto se demoro la publicacion hacia IA
    DURACION_PUBLICACION_MQTT.labels(
        destino="ia",
    ).observe(
        perf_counter() - inicio_ia
    )

    ## registra la cantidad de eventos publicados correctamente
    EVENTOS_MQTT_PUBLICADOS_TOTAL.labels(
        destino="ia",
    ).inc()

    ## registra la publicacion exitosa hacia IA
    ## manteniendo el mismo trace_id del evento.
    registrar_evento(
        logger,
        "Evento publicado hacia IA",
        componente="worker-publicador",
        evento="mqtt_ia_publicado",
        trace_id=evento.get(
            "trace_id"
        ),
        transaccion_id=evento.get(
            "transaccion_id"
        ),
        estado=evento.get(
            "estado"
        ),
        motivo=evento.get(
            "motivo"
        ),
        clave_idempotencia=evento.get(
            "clave_idempotencia"
        ),
        nivel=logging.DEBUG,
    )


## procesa un unico evento obtenido desde Redis Stream
async def procesar_evento(
    cliente_redis,
    cliente_mqtt,
    id_evento: str,
    datos_evento: dict,
) -> None:

    ## recuperacion del trace_id y transaccion_id,
    ## de una transaccion en concreto
    trace_id = datos_evento.get(
        "trace_id"
    )

    transaccion_id = datos_evento.get(
        "transaccion_id"
    )

    ## registra una entrega del Redis Stream.
    ## un mismo evento puede incrementar nuevamente esta metrica
    ## si debe recuperarse despues de un fallo
    EVENTOS_STREAM_RECIBIDOS_TOTAL.inc()

    ## registra que el evento fue tomado desde Redis Stream.
    registrar_evento(
        logger,
        "Evento recibido desde Redis Stream",
        componente="worker-publicador",
        evento="evento_stream_recibido",
        trace_id=trace_id,
        transaccion_id=transaccion_id,
        estado=datos_evento.get(
            "estado"
        ),
        motivo=datos_evento.get(
            "motivo"
        ),
        evento_id=id_evento,
        clave_idempotencia=datos_evento.get(
            "clave_idempotencia"
        ),
        nivel=logging.DEBUG,
    )

    try:

        ## se publica cada evento en mqtt
        await publicar_evento_mqtt(
            cliente_mqtt,
            datos_evento,
        )

        ## marca este evento dentro del stream como hecha,
        ## para que no la vuelva a mandar.
        ## solamente se confirma despues de que las dos
        ## publicaciones MQTT hayan terminado correctamente
        await cliente_redis.xack(
            settings.redis_stream_transacciones,
            settings.redis_consumer_group_mqtt,
            id_evento,
        )

        ## registra la confirmacion del evento dentro del
        ## consumer group despues de publicar correctamente.
        registrar_evento(
            logger,
            "Evento confirmado en Redis Stream",
            componente="worker-publicador",
            evento="evento_stream_confirmado",
            trace_id=trace_id,
            transaccion_id=transaccion_id,
            estado=datos_evento.get(
                "estado"
            ),
            motivo=datos_evento.get(
                "motivo"
            ),
            evento_id=id_evento,
            clave_idempotencia=datos_evento.get(
                "clave_idempotencia"
            ),
            nivel=logging.DEBUG,
        )

    except Exception:

        ## se genera un unico log completo por error.
        ## incluye el traceback y la informacion necesaria
        ## para poder rastrear la transaccion
        logger.exception(
            "Error procesando evento del Redis Stream",
            extra={
                "componente": "worker-publicador",
                "evento": "evento_publicacion_error",
                "trace_id": trace_id,
                "transaccion_id": transaccion_id,
                "estado": datos_evento.get(
                    "estado"
                ),
                "motivo": datos_evento.get(
                    "motivo"
                ),
                "evento_id": id_evento,
            },
        )

        ## propaga el error para detener el consumo.
        ## de esta forma no se siguen leyendo miles de eventos
        ## mientras MQTT se encuentra desconectado
        raise


## recupera mensajes que quedaron pendientes debido
## a la caida o reinicio de otro consumidor
async def recuperar_eventos_pendientes(
    cliente_redis,
    cliente_mqtt,
) -> int:

    inicio_busqueda = "0-0"

    total_recuperados = 0

    while True:

        try:

            respuesta = await cliente_redis.xautoclaim(
                name=settings.redis_stream_transacciones,
                groupname=settings.redis_consumer_group_mqtt,
                consumername=CONSUMIDOR_ID,
                min_idle_time=TIEMPO_MINIMO_PENDING_MS,
                start_id=inicio_busqueda,
                count=TAMANIO_LOTE_STREAM,
            )

        except RedisError:

            logger.exception(
                "Error recuperando eventos pendientes de Redis Stream"
            )

            raise

        ## Redis puede devolver:
        ##
        ## [
        ##     siguiente_id,
        ##     [(id_evento, datos), ...],
        ##     ids_eliminados
        ## ]
        ##
        ## la tercera posicion puede depender de la version
        ## de Redis/redis-py
        siguiente_id = respuesta[0]

        eventos = respuesta[1]

        ## si existen eventos recuperados se procesan
        ## uno por uno y solamente se hace XACK despues
        ## de publicar correctamente en MQTT
        for id_evento, datos_evento in eventos:

            await procesar_evento(
                cliente_redis,
                cliente_mqtt,
                id_evento,
                datos_evento,
            )

            total_recuperados += 1

        ## "0-0" indica que Redis termino de recorrer
        ## la lista de pendientes disponible
        if siguiente_id == "0-0":
            break

        ## si Redis utiliza bytes se contempla tambien
        ## esa representacion
        if siguiente_id == b"0-0":
            break

        ## continua desde la posicion indicada por Redis
        inicio_busqueda = siguiente_id

    return total_recuperados


## procesa eventos nuevos desde Redis Stream
async def procesar_eventos_nuevos(
    cliente_redis,
    cliente_mqtt,
) -> None:

    while True: ## mantiene siempre activo el worker

        ## lee los primeros mensajes que ningun otro
        ## worker del grupo haya atendido
        try:

            mensajes = await cliente_redis.xreadgroup(
                groupname=settings.redis_consumer_group_mqtt,
                consumername=CONSUMIDOR_ID,
                streams={
                    settings.redis_stream_transacciones: ">"
                },
                count=TAMANIO_LOTE_STREAM,
                block=5000,
            )

        except RedisError:

            logger.exception(
                "Error temporal leyendo Redis Stream"
            )

            await asyncio.sleep(1)

            continue

        ## si no existen mensajes continua
        if not mensajes:
            continue

        for _, eventos in mensajes: ## recorrer los streams que devolvió la consulta a Redis

            for id_evento, datos_evento in eventos: ## recorrer cada uno de los mensajes individuales dentro de la lista

                await procesar_evento(
                    cliente_redis,
                    cliente_mqtt,
                    id_evento,
                    datos_evento,
                )


## funcion que consume eventos de redis stream
## y los publica en mqtt
async def procesar_eventos() -> None:

    cliente_redis = crear_cliente_redis()

    logger.info(
        "Worker publicador conectado/configurado para Redis Stream: %s",
        settings.redis_stream_transacciones,
    )

    await crear_grupo_consumidores(
        cliente_redis
    )

    logger.info(
        "Consumer group listo: %s",
        settings.redis_consumer_group_mqtt,
    )

    ## mantiene vivo el worker incluso si MQTT se reinicia
    ## o la conexion se pierde temporalmente
    while True:

        try:

            ## se crea una nueva conexion MQTT en cada intento.
            ## si el broker cae, el context manager termina
            ## y en el siguiente ciclo se crea un cliente nuevo
            async with crear_cliente_mqtt() as cliente_mqtt:

                logger.info(
                    "Worker publicador conectado a MQTT"
                )

                ## antes de leer eventos nuevos se recuperan
                ## mensajes pendientes de consumidores anteriores
                total_recuperados = (
                    await recuperar_eventos_pendientes(
                        cliente_redis,
                        cliente_mqtt,
                    )
                )

                ## solamente se genera un log cuando realmente
                ## hubo eventos pendientes recuperados
                if total_recuperados > 0:

                    logger.info(
                        "Recuperacion de Redis Stream completada. "
                        "eventos_recuperados=%s consumidor=%s",
                        total_recuperados,
                        CONSUMIDOR_ID,
                    )

                ## despues de recuperar los pendientes
                ## comienza el consumo normal de mensajes nuevos
                await procesar_eventos_nuevos(
                    cliente_redis,
                    cliente_mqtt,
                )

        except asyncio.CancelledError:

            ## permite finalizar correctamente el worker
            ## cuando el proceso recibe una señal de cierre
            raise

        except Exception:

            ## no se vuelve a registrar el traceback aqui porque
            ## procesar_evento ya registro el error completo.
            ## este log solamente indica que se iniciara
            ## un nuevo intento de conexion
            logger.warning(
                "Conexion MQTT interrumpida. "
                "Se reintentara en %s segundo(s)",
                TIEMPO_REINTENTO_MQTT_SEGUNDOS,
            )

            await asyncio.sleep(
                TIEMPO_REINTENTO_MQTT_SEGUNDOS
            )


## inicia el worker
async def main() -> None:

    configurar_logging()

    start_http_server(
        9101
    )

    logger.info(
        "Servidor de metricas iniciado en puerto 9101"
    )

    logger.info(
        "Worker publicador iniciado. consumidor=%s",
        CONSUMIDOR_ID,
    )

    await procesar_eventos()


if __name__ == "__main__":

    asyncio.run(
        main()
    )
