from urllib.parse import urlparse

import paho.mqtt.client as mqtt

from app.config.settings import settings


## crea el cliente mqtt usado por el worker de ia
def crear_cliente_mqtt(
    client_id: str,
) -> mqtt.Client:

    mqtt_config = urlparse(
        settings.mqtt_url
    )

    if mqtt_config.scheme not in (
        "mqtt",
        "tcp",
    ):
        raise RuntimeError(
            f"Esquema MQTT no soportado: {mqtt_config.scheme}"
        )

    if not mqtt_config.hostname:
        raise RuntimeError(
            "MQTT_URL no contiene un host valido"
        )

    cliente = mqtt.Client(
        callback_api_version=(
            mqtt.CallbackAPIVersion.VERSION2
        ),
        client_id=client_id,
        clean_session=False,
        protocol=mqtt.MQTTv311,
        manual_ack=True,
    )

    if mqtt_config.username:

        cliente.username_pw_set(
            username=mqtt_config.username,
            password=mqtt_config.password,
        )

    cliente._smartbancs_host = mqtt_config.hostname
    cliente._smartbancs_port = mqtt_config.port or 1883

    return cliente
