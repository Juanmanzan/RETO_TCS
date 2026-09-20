from app.esquemas.cuentas import CuentaClienteResponse
from app.infraestructura.postgres.conexion import SesionPostgresql
from app.repositorios.consultas import listar_cuentas_clientes


## servicio de lectura para cuentas, independiente del procesamiento de transacciones
async def listar_cuentas_con_cliente() -> list[CuentaClienteResponse]:

    async with SesionPostgresql() as sesion:

        cuentas = await listar_cuentas_clientes(
            sesion
        )

    return [
        CuentaClienteResponse(
            **cuenta
        )
        for cuenta in cuentas
    ]
