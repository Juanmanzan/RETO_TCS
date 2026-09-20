import importlib
import sys

## test que permite verificar que settings.py cargue correctamente las variables de entorno.
def test_cargar_settings(monkeypatch):
    monkeypatch.setenv(
        "REDIS_URL",
        "redis://app_user:password@redis:6379/0",
    )
    monkeypatch.setenv(
        "REDIS_STREAM_TRANSACCIONES",
        "stream:transacciones",
    )
    monkeypatch.setenv(
        "REDIS_CONSUMER_GROUP_MQTT",
        "grupo:mqtt",
    )
    monkeypatch.setenv(
        "REDIS_MAX_CONNECTIONS",
        "800",
    )
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://app_user:password@postgres:5432/smartbancs",
    )
    monkeypatch.setenv(
        "MQTT_URL",
        "mqtt://app_user:password@mqtt:1883",
    )
    monkeypatch.setenv(
        "MQTT_TOPIC_PERSISTENCIA",
        "smartbancs/transacciones/persistencia",
    )
    monkeypatch.setenv(
        "MQTT_TOPIC_IA",
        "smartbancs/transacciones/ia",
    )

    # elimina el modulo si ya fue cargado para que vuelva a leer las variables
    sys.modules.pop("app.config.settings", None)
    modulo = importlib.import_module("app.config.settings")
    settings = modulo.settings

    assert settings.redis_url == "redis://app_user:password@redis:6379/0"
    assert settings.redis_max_connections == 800
    assert settings.redis_stream_transacciones == "stream:transacciones"
    assert settings.redis_consumer_group_mqtt == "grupo:mqtt"
    assert settings.database_url== "postgresql+asyncpg://app_user:password@postgres:5432/smartbancs"
    assert settings.mqtt_url == "mqtt://app_user:password@mqtt:1883"
    assert settings.mqtt_topic_persistencia== "smartbancs/transacciones/persistencia"
    assert settings.mqtt_topic_ia == "smartbancs/transacciones/ia"
