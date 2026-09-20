from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.cliente import Cliente
from app.modelos.cuenta import Cuenta
from app.modelos.recomendacion_ia import RecomendacionIa
from app.modelos.transaccion import Transaccion


@dataclass(frozen=True)
class DatosCuentaCliente:
    cliente_id: int
    cuenta_id: int
    ingresos_mensuales: Decimal
    gastos_mensuales: Decimal
    saldo: Decimal


## obtiene la informacion necesaria para que la ia pueda
## calcular la recomendacion del cliente
async def obtener_datos_cuenta_cliente(
    sesion: AsyncSession,
    cuenta_origen_id: int,
) -> DatosCuentaCliente | None:

    sentencia = (
        select(
            Cliente.id.label("cliente_id"),
            Cuenta.id.label("cuenta_id"),
            Cliente.ingresos_mensuales,
            Cliente.gastos_mensuales,
            Cuenta.saldo_centavos,
        )
        .join(
            Cuenta,
            Cuenta.cliente_id == Cliente.id,
        )
        .where(
            Cuenta.id == cuenta_origen_id
        )
    )

    resultado = await sesion.execute(
        sentencia
    )

    fila = resultado.mappings().one_or_none()

    if fila is None:
        return None

    return DatosCuentaCliente(
        cliente_id=fila["cliente_id"],
        cuenta_id=fila["cuenta_id"],
        ingresos_mensuales=fila["ingresos_mensuales"],
        gastos_mensuales=fila["gastos_mensuales"],
        saldo=Decimal(fila["saldo_centavos"]) / Decimal(100),
    )


## verifica si la transaccion ya existe en postgres
## antes de guardar la recomendacion con su llave foranea
async def existe_transaccion(
    sesion: AsyncSession,
    transaccion_id: str,
) -> bool:

    sentencia = (
        select(
            Transaccion.transaccion_id
        )
        .where(
            Transaccion.transaccion_id == transaccion_id
        )
        .limit(1)
    )

    resultado = await sesion.execute(
        sentencia
    )

    return resultado.scalar_one_or_none() is not None


## evita guardar la misma recomendacion mas de una vez
async def existe_recomendacion(
    sesion: AsyncSession,
    transaccion_id: str,
) -> bool:

    sentencia = (
        select(
            RecomendacionIa.id
        )
        .where(
            RecomendacionIa.transaccion_id == transaccion_id
        )
        .limit(1)
    )

    resultado = await sesion.execute(
        sentencia
    )

    return resultado.scalar_one_or_none() is not None
