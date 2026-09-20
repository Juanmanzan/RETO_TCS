from urllib.parse import urlparse
from aiomqtt import Client
from app.config.settings import settings

## funcion que crea un cliente mqtt
def crear_cliente_mqtt() -> Client:

    url_mqtt = urlparse(settings.mqtt_url)
    return Client(
        hostname=url_mqtt.hostname,
        port=url_mqtt.port or 1883,
        username=url_mqtt.username,
        password=url_mqtt.password,
    )