import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:

    # url de conexion hacia redis
    redis_url: str
    # stream principal donde se registran las transacciones procesadas
    redis_stream_transacciones: str
    # grupo encargado de consumir los eventos del stream y enviarlos a mqtt
    redis_consumer_group_mqtt: str
    # url de conexion hacia postgresql
    database_url: str
    # url de conexion hacia mqtt
    mqtt_url: str
    # topic utilizado para enviar las transacciones hacia persistencia
    mqtt_topic_persistencia: str
    # topic utilizado para enviar las transacciones hacia el servicio de ia
    mqtt_topic_ia: str

## funcion que carga los parametros del .env
def cargar_settings() -> Settings:

    # obtiene la url de conexion hacia redis
    redis_url = os.getenv("REDIS_URL")
    # obtiene el nombre del stream principal de transacciones
    redis_stream_transacciones = os.getenv(
        "REDIS_STREAM_TRANSACCIONES",
        "stream:transacciones",
    )
    # obtiene el grupo encargado de consumir los eventos para mqtt
    redis_consumer_group_mqtt = os.getenv(
        "REDIS_CONSUMER_GROUP_MQTT",
        "grupo:mqtt",
    )
    # obtiene la url de conexion hacia postgresql
    database_url = os.getenv("DATABASE_URL")
    # obtiene la url de conexion hacia mqtt
    mqtt_url = os.getenv("MQTT_URL")
    # obtiene el topic utilizado para persistencia
    mqtt_topic_persistencia = os.getenv(
        "MQTT_TOPIC_PERSISTENCIA",
        "smartbancs/transacciones/persistencia",
    )
    # obtiene el topic utilizado para procesamiento de ia
    mqtt_topic_ia = os.getenv(
        "MQTT_TOPIC_IA",
        "smartbancs/transacciones/ia",
    )

    # verifica que redis este configurado
    if not redis_url:
        raise RuntimeError(
            "REDIS_URL no esta configurada"
        )

    # verifica que postgresql este configurado
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL no esta configurada"
        )

    # verifica que mqtt este configurado
    if not mqtt_url:
        raise RuntimeError(
            "MQTT_URL no esta configurada"
        )

    return Settings(
        redis_url=redis_url,
        redis_stream_transacciones=redis_stream_transacciones,
        redis_consumer_group_mqtt=redis_consumer_group_mqtt,
        database_url=database_url,
        mqtt_url=mqtt_url,
        mqtt_topic_persistencia=mqtt_topic_persistencia,
        mqtt_topic_ia=mqtt_topic_ia,
    )


settings = cargar_settings()