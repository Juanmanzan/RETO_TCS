import asyncio
import json
import logging
from dataclasses import dataclass
from decimal import Decimal

import httpx
import paho.mqtt.client as mqtt
from prometheus_client import start_http_server

from app.config.settings import settings
from app.esquemas.recomendaciones import (
    NotificacionRecomendacion,
    SolicitudRecomendacion,
)
from app.infraestructura.mensajeria.conexion import (
    crear_cliente_mqtt,
)
from app.infraestructura.observabilidad.logging import (
    configurar_logging,
    registrar_evento,
)
from app.infraestructura.observabilidad.metricas import (
    ERRORES_IA_TOTAL,
    EVENTOS_IA_DESCARTADOS_TOTAL,
    EVENTOS_IA_RECIBIDOS_TOTAL,
    RECOMENDACIONES_PERSISTIDAS_TOTAL,
)
from app.servicios.recomendaciones import (
    procesar_recomendacion_worker,
)


logger = logging.getLogger(__name__)


@dataclass
class MensajeMqtt:
    payload: bytes
    mid: int
    qos: int


## convierte el evento de transaccion en una solicitud para la ia
def construir_solicitud(
    mensaje: MensajeMqtt,
) -> SolicitudRecomendacion:

    datos = json.loads(
        mensaje.payload.decode("utf-8")
    )

    return SolicitudRecomendacion(
        cuenta_origen_id=int(
            datos["cuenta_origen_id"]
        ),
        ## el evento llega con el monto en centavos
        ## igual que se guarda en transacciones
        monto_transferencia=(
            Decimal(
                str(
                    datos["monto"]
                )
            )
            / Decimal(100)
        ),
        transaccion_id=datos.get(
            "transaccion_id"
        ),
        trace_id=datos.get(
            "trace_id"
        ),
    )


## avisa a la api para que envie la recomendacion por websocket
async def publicar_websocket(
    recomendacion: NotificacionRecomendacion,
) -> None:

    async with httpx.AsyncClient(
        timeout=3.0,
    ) as cliente:

        await cliente.post(
            f"{settings.api_ia_url}/recomendaciones/notificar",
            json=recomendacion.model_dump(
                mode="json"
            ),
        )


## procesa un mensaje recibido desde mqtt
async def procesar_mensaje(
    cliente: mqtt.Client,
    mensaje: MensajeMqtt,
) -> None:

    try:

        solicitud = construir_solicitud(
            mensaje
        )

    except (
        json.JSONDecodeError,
        UnicodeDecodeError,
        KeyError,
        TypeError,
        ValueError,
    ):

        ERRORES_IA_TOTAL.labels(
            tipo="payload_invalido"
        ).inc()

        EVENTOS_IA_DESCARTADOS_TOTAL.labels(
            motivo="payload_invalido"
        ).inc()

        cliente.ack(
            mensaje.mid,
            mensaje.qos,
        )

        return

    EVENTOS_IA_RECIBIDOS_TOTAL.inc()

    ## primer log para rastrear por trace_id
    ## cuando el evento llega desde el publicador
    registrar_evento(
        logger,
        "Evento recibido para IA",
        componente="worker-ia",
        evento="evento_ia_recibido",
        trace_id=solicitud.trace_id,
        transaccion_id=solicitud.transaccion_id,
        cuenta_origen_id=solicitud.cuenta_origen_id,
    )

    try:

        recomendacion, resultado_persistencia = (
            await procesar_recomendacion_worker(
                solicitud
            )
        )

        if resultado_persistencia.insertada:

            RECOMENDACIONES_PERSISTIDAS_TOTAL.inc()

        notificacion = NotificacionRecomendacion(
            **recomendacion.model_dump(),
            recomendacion_id=(
                resultado_persistencia.recomendacion_id
            ),
        )

        await publicar_websocket(
            notificacion
        )

        ## segundo log para confirmar que la ia ya termino
        ## y dejo lista la recomendacion
        registrar_evento(
            logger,
            "Recomendacion procesada por IA",
            componente="worker-ia",
            evento="recomendacion_ia_procesada",
            trace_id=recomendacion.trace_id,
            transaccion_id=recomendacion.transaccion_id,
            cliente_id=recomendacion.id_usuario,
            cuenta_origen_id=recomendacion.cuenta_origen_id,
        )

        cliente.ack(
            mensaje.mid,
            mensaje.qos,
        )

    except Exception:

        ERRORES_IA_TOTAL.labels(
            tipo="procesamiento"
        ).inc()

        logger.exception(
            "Error procesando recomendacion de IA"
        )


## consume la cola interna limitando cuantas recomendaciones
## se procesan al mismo tiempo
async def consumir_cola(
    cola: asyncio.Queue,
    cliente: mqtt.Client,
) -> None:

    semaforo = asyncio.Semaphore(
        settings.ia_concurrencia
    )

    async def procesar_con_limite(
        mensaje: MensajeMqtt,
    ) -> None:

        async with semaforo:

            try:

                await procesar_mensaje(
                    cliente=cliente,
                    mensaje=mensaje,
                )

            finally:

                cola.task_done()

    while True:

        mensaje = await cola.get()

        asyncio.create_task(
            procesar_con_limite(
                mensaje
            )
        )


async def ejecutar_worker() -> None:

    start_http_server(
        9103
    )

    logger.info(
        "Servidor de metricas del worker-ia iniciado en puerto 9103"
    )

    loop = asyncio.get_running_loop()

    cola: asyncio.Queue[MensajeMqtt] = asyncio.Queue(
        maxsize=5000
    )

    cliente = crear_cliente_mqtt(
        client_id="worker-ia"
    )

    def encolar_mensaje(
        evento: MensajeMqtt,
    ) -> None:

        try:

            cola.put_nowait(
                evento
            )

        except asyncio.QueueFull:

            EVENTOS_IA_DESCARTADOS_TOTAL.labels(
                motivo="cola_llena"
            ).inc()

    def on_connect(
        client,
        userdata,
        flags,
        reason_code,
        properties,
    ) -> None:

        if reason_code.is_failure:

            logger.error(
                "Error conectando worker de ia a MQTT: %s",
                reason_code,
            )

            return

        logger.info(
            "Worker de ia conectado a MQTT"
        )

        resultado, _ = client.subscribe(
            settings.mqtt_topic_ia,
            qos=1,
        )

        if resultado != mqtt.MQTT_ERR_SUCCESS:

            logger.error(
                "No se pudo realizar la suscripcion al topic %s",
                settings.mqtt_topic_ia,
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
            encolar_mensaje,
            evento,
        )

    cliente.on_connect = on_connect
    cliente.on_message = on_message

    cliente.connect(
        host=cliente._smartbancs_host,
        port=cliente._smartbancs_port,
        keepalive=60,
    )

    cliente.loop_start()

    logger.info(
        "Worker de ia iniciado"
    )

    try:

        await consumir_cola(
            cola=cola,
            cliente=cliente,
        )

    finally:

        cliente.loop_stop()
        cliente.disconnect()


if __name__ == "__main__":

    configurar_logging()

    asyncio.run(
        ejecutar_worker()
    )
