from fastapi import APIRouter, status

from app.esquemas.cuentas import CuentaClienteResponse
from app.servicios.cuentas import listar_cuentas_con_cliente


router = APIRouter(
    prefix="/api/cuentas",
    tags=["cuentas"],
)


## endpoint de solo lectura para listar cuentas con el cliente asociado
@router.get(
    "",
    response_model=list[CuentaClienteResponse],
    status_code=status.HTTP_200_OK,
)
async def listar_cuentas() -> list[CuentaClienteResponse]:

    return await listar_cuentas_con_cliente()
