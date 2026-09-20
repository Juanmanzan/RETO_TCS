from prometheus_client import (
    Counter,
    Histogram,
)


## cantidad total de transacciones procesadas
## permite separar las transacciones segun su estado:
## COMPLETADA o RECHAZADA
TRANSACCIONES_TOTAL = Counter(
    "smartbancs_transacciones_total",
    "Cantidad total de transacciones procesadas por la API",
    [
        "estado",
        "motivo",
    ],
)


## cantidad de errores ocurridos durante el procesamiento
## de una transaccion
ERRORES_TRANSACCIONES_TOTAL = Counter(
    "smartbancs_errores_transacciones_total",
    "Cantidad total de errores durante el procesamiento de transacciones",
    ["tipo"],
)


## tiempo total que tarda el endpoint POST /api/transacciones
## desde que recibe la solicitud hasta que devuelve la respuesta
DURACION_HTTP_TRANSACCION = Histogram(
    "smartbancs_http_transaccion_duracion_seconds",
    "Tiempo de respuesta del endpoint POST /api/transacciones",
    buckets=(
        0.005,
        0.010,
        0.025,
        0.050,
        0.100,
        0.250,
        0.500,
        1.0,
        2.5,
        5.0,
    ),
)


## tiempo que tarda especificamente la ejecucion
## atomica de Redis/Lua
DURACION_REDIS_LUA = Histogram(
    "smartbancs_redis_lua_duracion_seconds",
    "Tiempo de ejecucion de la transferencia en Redis/Lua",
    buckets=(
        0.001,
        0.0025,
        0.005,
        0.010,
        0.025,
        0.050,
        0.100,
        0.250,
        0.500,
        1.0,
    ),
)


## cantidad de timeouts detectados
## el componente permite identificar donde se produjo
TIMEOUTS_TOTAL = Counter(
    "smartbancs_timeouts_total",
    "Cantidad total de timeouts detectados",
    ["componente"],
)

## cantidad de eventos recibidos desde Redis Stream
EVENTOS_STREAM_RECIBIDOS_TOTAL = Counter(
    "smartbancs_eventos_stream_recibidos_total",
    "Cantidad total de eventos recibidos desde Redis Stream",
)


## cantidad de eventos publicados hacia MQTT
## destino permite diferenciar persistencia e IA
EVENTOS_MQTT_PUBLICADOS_TOTAL = Counter(
    "smartbancs_eventos_mqtt_publicados_total",
    "Cantidad total de eventos publicados hacia MQTT",
    ["destino"],
)


## cantidad de errores al publicar eventos hacia MQTT
ERRORES_MQTT_TOTAL = Counter(
    "smartbancs_errores_mqtt_total",
    "Cantidad total de errores durante la publicacion MQTT",
    ["destino"],
)


## tiempo que tarda la publicacion MQTT
DURACION_PUBLICACION_MQTT = Histogram(
    "smartbancs_publicacion_mqtt_duracion_seconds",
    "Tiempo utilizado para publicar un evento hacia MQTT",
    ["destino"],
    buckets=(
        0.001,
        0.0025,
        0.005,
        0.010,
        0.025,
        0.050,
        0.100,
        0.250,
        0.500,
        1.0,
    ),
)

## cantidad de eventos recibidos por el worker de persistencia
EVENTOS_PERSISTENCIA_RECIBIDOS_TOTAL = Counter(
    "smartbancs_eventos_persistencia_recibidos_total",
    "Cantidad total de eventos recibidos por el worker de persistencia",
)


## cantidad de transacciones insertadas correctamente
EVENTOS_PERSISTIDOS_TOTAL = Counter(
    "smartbancs_eventos_persistidos_total",
    "Cantidad total de transacciones persistidas correctamente",
)


## cantidad de eventos duplicados detectados
EVENTOS_DUPLICADOS_TOTAL = Counter(
    "smartbancs_eventos_duplicados_total",
    "Cantidad total de eventos duplicados detectados durante la persistencia",
)


## cantidad de eventos enviados a la Dead Letter Queue
EVENTOS_DLQ_TOTAL = Counter(
    "smartbancs_eventos_dlq_total",
    "Cantidad total de eventos enviados a la Dead Letter Queue",
)


## errores detectados por el worker de persistencia
ERRORES_PERSISTENCIA_TOTAL = Counter(
    "smartbancs_errores_persistencia_total",
    "Cantidad total de errores detectados por el worker de persistencia",
    ["tipo"],
)


## tiempo total empleado por el worker en procesar y persistir un evento
DURACION_PERSISTENCIA = Histogram(
    "smartbancs_persistencia_duracion_seconds",
    "Tiempo total empleado por el worker para procesar un evento de persistencia",
    buckets=(
        0.001,
        0.0025,
        0.005,
        0.010,
        0.025,
        0.050,
        0.100,
        0.250,
        0.500,
        1.0,
        2.5,
        5.0,
    ),
)
