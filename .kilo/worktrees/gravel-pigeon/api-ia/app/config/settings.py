import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:

    # url de conexion hacia postgresql
    database_url: str
    # url de conexion hacia mqtt
    mqtt_url: str
    # topic donde llegan las transacciones para ia
    mqtt_topic_ia: str
    # url interna de la api de ia para avisar al websocket
    api_ia_url: str
    # numero maximo de recomendaciones procesadas a la vez
    ia_concurrencia: int


## funcion que carga los parametros del entorno
def cargar_settings() -> Settings:

    database_url = os.getenv(
        "DATABASE_URL"
    )

    mqtt_url = os.getenv(
        "MQTT_URL"
    )

    mqtt_topic_ia = os.getenv(
        "MQTT_TOPIC_IA",
        "smartbancs/transacciones/ia",
    )

    api_ia_url = os.getenv(
        "API_IA_URL",
        "http://api-ia:8000",
    )

    ia_concurrencia = int(
        os.getenv(
            "IA_CONCURRENCIA",
            "20",
        )
    )

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL no esta configurada"
        )

    if not mqtt_url:
        raise RuntimeError(
            "MQTT_URL no esta configurada"
        )

    return Settings(
        database_url=database_url,
        mqtt_url=mqtt_url,
        mqtt_topic_ia=mqtt_topic_ia,
        api_ia_url=api_ia_url,
        ia_concurrencia=ia_concurrencia,
    )


settings = cargar_settings()
