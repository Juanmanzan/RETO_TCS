import secrets
import uuid

## genera un identificar unico para la transaccion  UUID
## formatode salida TRX-123e4567-e89b-12d3-a456-426614174000
def generar_transaccion_id() -> str:
    return f"TRX-{uuid.uuid4().hex}"

## genera un token trace_id para seguir la transaccion por los diferentes modeulos
## del sistema, se empleo para generar token de 32 bytes aleatorio 
def generar_trace_id() -> str:
    return secrets.token_urlsafe(32)