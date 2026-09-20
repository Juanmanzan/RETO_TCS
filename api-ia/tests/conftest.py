import os


## variables minimas para que la configuracion de ia
## pueda cargarse durante las pruebas unitarias
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://app_user:password@postgres:5432/smartbancs",
)

os.environ.setdefault(
    "MQTT_URL",
    "mqtt://app_user:password@mqtt:1883",
)

os.environ.setdefault(
    "MQTT_TOPIC_IA",
    "smartbancs/transacciones/ia",
)
