import asyncio
import json
import logging
from dataclasses import dataclass
from time import perf_counter
from urllib.parse import urlparse

import paho.mqtt.client as mqtt

from prometheus_client import start_http_server

from app.config.settings import settings

from app.infraestructura.postgres.conexion import (
    SesionPostgresql,
)

from app.infraestructura.observabilidad.logging import (
    configurar_logging,
    registrar_evento,
)

from app.infraestructura.observabilidad.metricas import (
    DURACION_PERSISTENCIA,
    ERRORES_PERSISTENCIA_TOTAL,
    EVENTOS_DLQ_TOTAL,
    EVENTOS_DUPLICADOS_TOTAL,
    EVENTOS_PERSISTENCIA_RECIBIDOS_TOTAL,
    EVENTOS_PERSISTIDOS_TOTAL,
)

from app.modelos.transaccion import Transaccion

from app.repositorios.transacciones import (
    insertar_transacciones_lote,
)


logger = logging.getLogger(__name__)


## topic utilizado para almacenar mensajes que no pueden procesarse
## correctamente por errores permanentes en el payload
TOPIC_DLQ_PERSISTENCIA = (
    f"{settings.mqtt_topic_persistencia}/dlq"
)


## número máximo de mensajes que se persistirán dentro
## de una misma transacción PostgreSQL
TAMANIO_LOTE_PERSISTENCIA = 100


## tiempo máximo que el worker esperará para intentar completar
## un lote antes de persistir los mensajes ya disponibles
TIEMPO_ESPERA_LOTE_SEGUNDOS = 0.05


@dataclass
class MensajeMqtt:
    payload: bytes
    mid: int
    qos: int


@dataclass
class EventoPersistencia:
    mensaje: MensajeMqtt
    transaccion: Transaccion


def obtener_monto_centavos(
    datos: dict,
) -> int:

    ## El evento llega desde Redis Stream con el campo "monto"
    ## ya expresado en centavos. En PostgreSQL se persiste en
    ## transacciones.monto_centavos; no se usa una columna "saldo".
    monto = datos.get(
        "monto_centavos",
        datos["monto"],
    )

    return int(
        monto
    )


"""
    Convierte el evento MQTT en una Transaccion ORM.
    Los errores permanentes del payload se propagan de forma
    separada para evitar confundirlos con errores PostgreSQL.
    Esta función no realiza operaciones contra PostgreSQL.
"""
def construir_evento_persistencia(
    mensaje: MensajeMqtt,
) -> EventoPersistencia:

    datos = json.loads(
        mensaje.payload.decode("utf-8")
    )

    ## registra la cantidad de eventos recibidos desde MQTT.
    ## se utiliza una métrica en lugar de generar un log
    ## individual por cada evento.
    EVENTOS_PERSISTENCIA_RECIBIDOS_TOTAL.inc()

    transaccion = Transaccion(
        transaccion_id=datos["transaccion_id"],
        trace_id=datos["trace_id"],
        clave_idempotencia=datos["clave_idempotencia"],
        cuenta_origen_id=int(
            datos["cuenta_origen_id"]
        ),
        cuenta_destino_id=int(
            datos["cuenta_destino_id"]
        ),
        monto_centavos=obtener_monto_centavos(
            datos
        ),
        moneda=datos["moneda"],
        descripcion=datos.get(
            "descripcion"
        ),
        estado=datos["estado"],
        motivo=datos["motivo"],
    )

    return EventoPersistencia(
        mensaje=mensaje,
        transaccion=transaccion,
    )


##Persiste un conjunto de eventos utilizando una única sesión
##PostgreSQL y un único COMMIT.

async def persistir_lote_eventos(
    eventos: list[EventoPersistencia],
) -> bool:

    if not eventos:
        return True

    inicio_persistencia = perf_counter()

    transacciones = [
        evento.transaccion
        for evento in eventos
    ]

    async with SesionPostgresql() as sesion:

        ids_insertados = (
            await insertar_transacciones_lote(
                sesion=sesion,
                transacciones=transacciones,
            )
        )

    ## actualiza las métricas correspondientes a cada evento.
    ## no se generan logs individuales para evitar una carga
    ## excesiva durante pruebas de alto volumen.
    for evento in eventos:

        transaccion = evento.transaccion

        if (
            transaccion.transaccion_id
            in ids_insertados
        ):

            EVENTOS_PERSISTIDOS_TOTAL.inc()

            ## registra solamente las transacciones que fueron
            ## insertadas realmente en PostgreSQL. Esto permite
            ## buscarlas despues por trace_id sin confundirlas
            ## con duplicados descartados por idempotencia.
            registrar_evento(
                logger,
                "Transaccion persistida correctamente",
                componente="worker-persistencia",
                evento="transaccion_persistida",
                trace_id=transaccion.trace_id,
                transaccion_id=transaccion.transaccion_id,
                estado=transaccion.estado,
                motivo=transaccion.motivo,
                evento_id=str(
                    evento.mensaje.mid
                ),
                clave_idempotencia=transaccion.clave_idempotencia,
            )

        else:

            EVENTOS_DUPLICADOS_TOTAL.inc()

            ## un duplicado no se considera error debido a que
            ## PostgreSQL funciona como segunda defensa de idempotencia

    duracion = (
        perf_counter()
        - inicio_persistencia
    )

    ## se mantiene la métrica existente de duración.
    ## representa ahora el tiempo necesario para persistir
    ## el lote completo.
    DURACION_PERSISTENCIA.observe(
        duracion
    )

    ## se conserva un único log por lote.
    ## permite observar el tamaño real del batch y su duración
    ## sin generar miles de logs individuales por segundo.
    logger.info(
        "Lote PostgreSQL procesado. "
        "total=%s insertadas=%s duplicadas=%s duracion_ms=%.3f",
        len(eventos),
        len(ids_insertados),
        len(eventos) - len(ids_insertados),
        duracion * 1000,
    )

    return True


## publica en una Dead Letter Queue los mensajes que presentan
## errores permanentes y que nunca podrán procesarse correctamente
async def publicar_en_dlq(
    cliente: mqtt.Client,
    mensaje: MensajeMqtt,
    error: Exception,
) -> bool:

    payload_dlq = {
        "payload_original": mensaje.payload.decode(
            "utf-8",
            errors="replace",
        ),
        "tipo_error": type(error).__name__,
        "error": str(error),
        "mid": mensaje.mid,
    }

    try:

        resultado = cliente.publish(
            TOPIC_DLQ_PERSISTENCIA,
            payload=json.dumps(
                payload_dlq,
                ensure_ascii=False,
            ),
            qos=1,
        )

        ## espera la confirmacion de publicacion sin bloquear
        ## directamente el event loop de asyncio
        await asyncio.to_thread(
            resultado.wait_for_publish,
            5,
        )

        if not resultado.is_published():

            logger.error(
                "No se pudo confirmar publicacion del mensaje "
                "en DLQ. mid=%s",
                mensaje.mid,
            )

            return False

        logger.warning(
            "Evento invalido enviado a DLQ. "
            "mid=%s topic=%s",
            mensaje.mid,
            TOPIC_DLQ_PERSISTENCIA,
        )

        EVENTOS_DLQ_TOTAL.inc()

        return True

    except Exception:

        ERRORES_PERSISTENCIA_TOTAL.labels(
            tipo="dlq"
        ).inc()

        logger.exception(
            "Error publicando evento invalido "
            "en DLQ. mid=%s",
            mensaje.mid,
        )

        return False


## confirma manualmente un mensaje MQTT después de que
## su procesamiento haya finalizado correctamente
def confirmar_mensaje_mqtt(
    cliente: mqtt.Client,
    mensaje: MensajeMqtt,
) -> bool:

    resultado_ack = cliente.ack(
        mensaje.mid,
        mensaje.qos,
    )

    ## los ACK correctos no generan logs individuales.
    ## solamente se registra cuando ocurre un error.
    if resultado_ack == mqtt.MQTT_ERR_SUCCESS:
        return True

    logger.error(
        "No se pudo enviar ACK MQTT. "
        "mid=%s codigo=%s",
        mensaje.mid,
        resultado_ack,
    )

    return False


## intenta obtener varios mensajes de la cola para formar
## un lote de persistencia.
##
## el worker no espera obligatoriamente a llenar los 100
## mensajes: si se alcanza el tiempo máximo configurado,
## procesa inmediatamente los mensajes disponibles.
async def obtener_lote(
    cola: asyncio.Queue,
) -> list[MensajeMqtt]:

    primer_mensaje: MensajeMqtt = (
        await cola.get()
    )

    lote = [
        primer_mensaje
    ]

    loop = asyncio.get_running_loop()

    limite_tiempo = (
        loop.time()
        + TIEMPO_ESPERA_LOTE_SEGUNDOS
    )

    while (
        len(lote)
        < TAMANIO_LOTE_PERSISTENCIA
    ):

        tiempo_restante = (
            limite_tiempo
            - loop.time()
        )

        if tiempo_restante <= 0:
            break

        try:

            mensaje = await asyncio.wait_for(
                cola.get(),
                timeout=tiempo_restante,
            )

            lote.append(
                mensaje
            )

        except asyncio.TimeoutError:
            break

    return lote


##Consume los mensajes recibidos desde MQTT y controla
##cuándo se envía el ACK.
async def consumidor_persistencia(
    cola: asyncio.Queue,
    cliente: mqtt.Client,
) -> None:

    while True:

        lote_mensajes = await obtener_lote(
            cola
        )

        eventos_validos: list[
            EventoPersistencia
        ] = []

        try:

            ## primero se validan todos los mensajes del lote.
            ## los payload inválidos no deben ingresar dentro
            ## de la transacción PostgreSQL.
            for mensaje in lote_mensajes:

                try:

                    evento = (
                        construir_evento_persistencia(
                            mensaje
                        )
                    )

                    eventos_validos.append(
                        evento
                    )

                except (
                    json.JSONDecodeError,
                    UnicodeDecodeError,
                    KeyError,
                    TypeError,
                    ValueError,
                ) as error:

                    ERRORES_PERSISTENCIA_TOTAL.labels(
                        tipo="payload_invalido"
                    ).inc()

                    ## estos errores se consideran permanentes debido
                    ## a que volver a procesar el mismo payload no los
                    ## solucionará
                    logger.error(
                        "Evento MQTT invalido. "
                        "mid=%s error=%s payload=%r",
                        mensaje.mid,
                        error,
                        mensaje.payload,
                    )

                    ## antes de confirmar el mensaje original se intenta
                    ## conservarlo dentro de la Dead Letter Queue
                    enviado_dlq = await publicar_en_dlq(
                        cliente=cliente,
                        mensaje=mensaje,
                        error=error,
                    )

                    ## solo se confirma el mensaje original cuando ya
                    ## existe una copia dentro de la DLQ
                    if enviado_dlq:

                        resultado_ack = cliente.ack(
                            mensaje.mid,
                            mensaje.qos,
                        )

                        if (
                            resultado_ack
                            != mqtt.MQTT_ERR_SUCCESS
                        ):

                            logger.error(
                                "No se pudo enviar ACK para evento DLQ. "
                                "mid=%s codigo=%s",
                                mensaje.mid,
                                resultado_ack,
                            )

                    ## si la publicación en DLQ falla no se realiza ACK
                    ## para evitar perder definitivamente el mensaje

            ## si todos los mensajes del lote eran inválidos
            ## no es necesario abrir una transacción PostgreSQL
            if not eventos_validos:
                continue

            try:
                procesado = (
                    await persistir_lote_eventos(
                        eventos_validos
                    )
                )
            except Exception:
                ERRORES_PERSISTENCIA_TOTAL.labels(
                    tipo="temporal"
                ).inc()
                ## PostgreSQL caído, timeout, pérdida de conexión, etc.
                ## no se realiza ACK para evitar perder los eventos
                ## que pertenecen al lote
                logger.exception(
                    "Error temporal procesando lote MQTT. "
                    "total_eventos=%s",
                    len(eventos_validos),
                )
                continue
            if procesado:
                ## una transacción persistida o duplicada se considera
                ## correctamente procesada y puede confirmarse en MQTT
                ##
                ## todos los ACK se realizan únicamente después
                ## de que PostgreSQL haya ejecutado correctamente
                ## el COMMIT del lote completo.
                for evento in eventos_validos:

                    confirmar_mensaje_mqtt(
                        cliente=cliente,
                        mensaje=evento.mensaje,
                    )
        finally:

            ## cada mensaje obtenido mediante cola.get()
            ## debe finalizar exactamente con un task_done()
            for _ in lote_mensajes:
                cola.task_done()


async def ejecutar_worker() -> None:

    start_http_server(
        9102
    )
    logger.info(
        "Servidor de metricas del worker-persistencia "
        "iniciado en puerto 9102"
    )
    loop = asyncio.get_running_loop()
    cola: asyncio.Queue[
        MensajeMqtt
    ] = asyncio.Queue()
    mqtt_config = urlparse(
        settings.mqtt_url
    )
    if mqtt_config.scheme not in (
        "mqtt",
        "tcp",
    ):
        raise RuntimeError(
            f"Esquema MQTT no soportado: "
            f"{mqtt_config.scheme}"
        )
    if not mqtt_config.hostname:

        raise RuntimeError(
            "MQTT_URL no contiene un host valido"
        )
    cliente = mqtt.Client(
        callback_api_version=(
            mqtt.CallbackAPIVersion.VERSION2
        ),
        client_id="worker-persistencia",
        clean_session=False,
        protocol=mqtt.MQTTv311,
        manual_ack=True,
    )
    if mqtt_config.username:

        cliente.username_pw_set(
            username=mqtt_config.username,
            password=mqtt_config.password,
        )
    def on_connect(
        client,
        userdata,
        flags,
        reason_code,
        properties,
    ) -> None:
        if reason_code.is_failure:

            logger.error(
                "Error conectando worker de persistencia "
                "a MQTT: %s",
                reason_code,
            )

            return
        logger.info(
            "Worker de persistencia conectado a MQTT"
        )
        resultado, mid = client.subscribe(
            settings.mqtt_topic_persistencia,
            qos=1,
        )
        if resultado != mqtt.MQTT_ERR_SUCCESS:
            logger.error(
                "No se pudo realizar la suscripcion "
                "al topic %s. codigo=%s",
                settings.mqtt_topic_persistencia,
                resultado,
            )
            return
        logger.info(
            "Suscrito al topic: %s",
            settings.mqtt_topic_persistencia,
        )
    def on_disconnect(
        client,
        userdata,
        disconnect_flags,
        reason_code,
        properties,
    ) -> None:
        if reason_code != 0:
            logger.warning(
                "Conexion MQTT perdida: %s",
                  reason_code,
            )
        else:
            logger.info(
                "Worker desconectado de MQTT"
            )

    def on_message(
        client,
        userdata,
        mensaje,
    ) -> None:
        evento = MensajeMqtt(
            payload=mensaje.payload,
            mid=mensaje.mid,
            qos=mensaje.qos,
        )
        loop.call_soon_threadsafe(
            cola.put_nowait,
            evento,
        )

    cliente.on_connect = on_connect
    cliente.on_disconnect = on_disconnect
    cliente.on_message = on_message

    cliente.connect(
        host=mqtt_config.hostname,
        port=mqtt_config.port or 1883,
        keepalive=60,
    )
    cliente.loop_start()
    logger.info(
        "Worker de persistencia iniciado"
    )
    try:
        await consumidor_persistencia(
            cola=cola,
            cliente=cliente,
        )
    finally:

        cliente.loop_stop()
        cliente.disconnect()


if __name__ == "__main__":

    ## configura el formato estructurado de logs utilizado
    configurar_logging()

    asyncio.run(
        ejecutar_worker()
    )
