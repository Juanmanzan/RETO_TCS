from pydantic import BaseModel


## contrato de salida para listar cuentas con su cliente asociado
class CuentaClienteResponse(BaseModel):
    id_cuenta: int
    cliente: str
