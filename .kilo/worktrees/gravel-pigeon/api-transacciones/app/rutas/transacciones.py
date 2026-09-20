from fastapi import APIRouter, Depends, status

from app.esquemas.transacciones import (
    TransferenciaRequest,
    TransferenciaResponse,
)

from app.servicios.transacciones import (
    ServicioTransacciones,
)


router = APIRouter(
    prefix="/api/transacciones",
    tags=["transacciones"],
)

## obtiene la instancia del servicio de transacciones
def obtener_servicio_transacciones() -> ServicioTransacciones:

    raise RuntimeError(
        "el servicio de transacciones no ha sido inicializado"
    )

## endpoind de tipo post, valida que el request venga en el formato valido
@router.post(
    "",
    response_model=TransferenciaResponse,
    status_code=status.HTTP_200_OK,
)
## valida que el request tenga el formato valido
## llama al servicio para procesar transacciones 
async def crear_transferencia(
    transferencia: TransferenciaRequest,
    servicio: ServicioTransacciones = Depends(
        obtener_servicio_transacciones
    ),
) -> TransferenciaResponse:
    ## espera a que la transaccion se procese 
    return await servicio.procesar_transancion(
        transferencia
    )