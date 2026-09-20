from sqlalchemy import (
    func,
    select,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.cliente import Cliente
from app.modelos.cuenta import Cuenta


## consulta minima para listar cada cuenta con el nombre del cliente asociado
async def listar_cuentas_clientes(
    sesion: AsyncSession,
) -> list[dict[str, str | int]]:

    sentencia = (
        select(
            Cuenta.id.label("id_cuenta"),
            func.concat(
                Cliente.nombre,
                " ",
                Cliente.apellido,
            ).label("cliente"),
        )
        .join(
            Cliente,
            Cuenta.cliente_id == Cliente.id,
        )
        .order_by(
            Cuenta.id,
        )
    )

    resultado = await sesion.execute(
        sentencia
    )

    return [
        {
            "id_cuenta": fila.id_cuenta,
            "cliente": fila.cliente,
        }
        for fila in resultado.all()
    ]
