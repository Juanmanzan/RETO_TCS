from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.infraestructura.redis.conexion import (
    crear_cliente_redis,
)

from app.infraestructura.redis.scripts import (
    ScriptsRedis,
)

from app.registro_rutas import (
    registrar_rutas,
)

from app.rutas.transacciones import (
    obtener_servicio_transacciones,
)

from app.servicios.transacciones import (
    ServicioTransacciones,
)

from app.infraestructura.observabilidad.logging import (
    configurar_logging,
)

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    generate_latest,
    multiprocess,
)

##controla la inicializacion y cierre de los recursos
##utilizados durante la vida de la aplicacion
@asynccontextmanager
async def lifespan(app: FastAPI):
    
    # crea el cliente asincrono de redis
    cliente_redis = crear_cliente_redis()

    # verifica que redis se encuentre disponible
    await cliente_redis.ping()

    # crea el manejador de scripts lua
    scripts_redis = ScriptsRedis(
        cliente_redis
    )

    # carga el script de transferencia en redis
    await scripts_redis.cargar_script_transferencia()

    # crea el servicio principal de transacciones
    servicio_transacciones = ServicioTransacciones(
        scripts_redis
    )

    # almacena los recursos para reutilizarlos durante las peticiones
    app.state.cliente_redis = cliente_redis
    app.state.scripts_redis = scripts_redis
    app.state.servicio_transacciones = servicio_transacciones

    yield

    # cierra correctamente el cliente redis al detener la aplicacion
    await cliente_redis.aclose()

configurar_logging()

app = FastAPI(
    title="API transacciones",
    description="microservicio encargado del procesamiento de transacciones",
    version="1.0.0",
    lifespan=lifespan,
)

## permite que la ui local consuma la api desde el navegador
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def obtener_servicio_desde_app(
    request: Request,
) -> ServicioTransacciones:
    """
    obtiene el servicio de transacciones inicializado
    durante el lifespan de la aplicacion
    """

    return request.app.state.servicio_transacciones


# reemplaza la dependencia temporal definida en la ruta
app.dependency_overrides[
    obtener_servicio_transacciones
] = obtener_servicio_desde_app

# registra las rutas de la aplicacion
registrar_rutas(app)

## enpoint para verificar que el servicio de fastapi se inicializo 
@app.get(
    "/health",
    tags=["health"],
)
async def health():
    """
    verifica que el servicio se encuentre disponible
    """

    return {
        "status": "ok",
        "service": "api-transacciones",
    }
## endpoint para exponer las metricas de rendimiento, tiempo de respuesta etc
@app.get("/metrics", include_in_schema=False)
async def metricas():

    directorio_multiproceso = os.getenv(
        "PROMETHEUS_MULTIPROC_DIR"
    )

    if directorio_multiproceso:

        registro = CollectorRegistry()

        multiprocess.MultiProcessCollector(
            registro
        )

        contenido = generate_latest(
            registro
        )

    else:

        contenido = generate_latest()

    return Response(
        content=contenido,
        media_type=CONTENT_TYPE_LATEST,
    )
