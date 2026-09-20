from fastapi import (
    FastAPI,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    generate_latest,
)

from app.esquemas.recomendaciones import (
    NotificacionRecomendacion,
)
from app.infraestructura.observabilidad.logging import (
    configurar_logging,
)
from app.servicios.websocket import gestor_websocket


app = FastAPI(
    title="API de IA",
    version="1.0.0",
)

## permite que la ui local se conecte al websocket de recomendaciones
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:

    configurar_logging()


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "api-ia",
    }


@app.get("/metrics", include_in_schema=False)
async def metricas():
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.post("/recomendaciones/notificar")
async def recomendaciones_notificar(
    recomendacion: NotificacionRecomendacion,
):

    ## endpoint interno usado por el worker para mandar
    ## la recomendacion ya procesada hacia los websocket
    await gestor_websocket.publicar(
        recomendacion.model_dump()
    )

    return {
        "status": "ok",
    }


@app.websocket("/ws/recomendaciones")
async def websocket_recomendaciones(
    websocket: WebSocket,
):

    await gestor_websocket.conectar(
        websocket
    )

    try:

        while True:

            ## mantiene vivo el socket.
            ## mas adelante se puede usar para filtros por cliente
            await websocket.receive_text()

    except WebSocketDisconnect:

        gestor_websocket.desconectar(
            websocket
        )
