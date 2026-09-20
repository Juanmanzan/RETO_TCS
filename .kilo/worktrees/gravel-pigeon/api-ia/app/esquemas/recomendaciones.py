from decimal import Decimal

from pydantic import BaseModel


class SolicitudRecomendacion(BaseModel):
    id_usuario: int | None = None
    cuenta_origen_id: int
    monto_transferencia: Decimal
    transaccion_id: str | None = None
    trace_id: str | None = None


class RespuestaRecomendacion(BaseModel):
    id_usuario: int
    cuenta_origen_id: int
    transaccion_id: str | None
    trace_id: str | None
    capacidad_financiera: str
    impacto_liquidez: str
    recomendacion: str
    version_modelo: str = "reglas-v1"


class NotificacionRecomendacion(RespuestaRecomendacion):
    recomendacion_id: int | None = None
