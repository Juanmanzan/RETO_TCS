from collections.abc import Sequence

from sqlalchemy import update
from app.modelos.cuenta import Cuenta
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modelos.transaccion import Transaccion


async def actualizar_saldos_transaccion(
    sesion: AsyncSession,
    transaccion: Transaccion,
) -> None:

    if transaccion.estado != "COMPLETADA":
        return

    await sesion.execute(
        update(Cuenta)
        .where(
            Cuenta.id == transaccion.cuenta_origen_id
        )
        .values(
            saldo_centavos=(
                Cuenta.saldo_centavos
                - transaccion.monto_centavos
            )
        )
    )

    await sesion.execute(
        update(Cuenta)
        .where(
            Cuenta.id == transaccion.cuenta_destino_id
        )
        .values(
            saldo_centavos=(
                Cuenta.saldo_centavos
                + transaccion.monto_centavos
            )
        )
    )


"""
    Inserta una transacción en PostgreSQL.

    Retorna:
        True:
            la transacción fue insertada.

        False:
            la transacción ya existía y fue ignorada
            por idempotencia.

    Esta función se conserva para operaciones individuales.
"""
async def insertar_transaccion(
    sesion: AsyncSession,
    transaccion: Transaccion,
) -> bool:

    sentencia = (
        insert(Transaccion)
        .values(
            transaccion_id=transaccion.transaccion_id,
            trace_id=transaccion.trace_id,
            clave_idempotencia=transaccion.clave_idempotencia,
            cuenta_origen_id=transaccion.cuenta_origen_id,
            cuenta_destino_id=transaccion.cuenta_destino_id,
            monto_centavos=transaccion.monto_centavos,
            moneda=transaccion.moneda,
            descripcion=transaccion.descripcion,
            estado=transaccion.estado,
            motivo=transaccion.motivo,
        )
        ## no se especifica una restricción concreta porque existen
        ## dos mecanismos de idempotencia:
        ## transaccion_id PRIMARY KEY
        ## clave_idempotencia UNIQUE
        .on_conflict_do_nothing()
        .returning(
            Transaccion.transaccion_id
        )
    )

    resultado = await sesion.execute(
        sentencia
    )

    transaccion_insertada = (
        resultado.scalar_one_or_none()
    )

    if transaccion_insertada is not None:
        await actualizar_saldos_transaccion(
            sesion=sesion,
            transaccion=transaccion,
        )

    await sesion.commit()

    return transaccion_insertada is not None


"""
    Inserta un conjunto de transacciones utilizando una única
    operación hacia PostgreSQL y un único COMMIT.

    Retorna un conjunto con los transaccion_id que realmente
    fueron insertados.

    Las transacciones que no aparezcan dentro del conjunto
    retornado fueron ignoradas por PostgreSQL debido a una
    restricción de idempotencia.

    Si PostgreSQL presenta un error se realiza ROLLBACK y la
    excepción se propaga al worker para evitar confirmar los
    mensajes MQTT.
"""
async def insertar_transacciones_lote(
    sesion: AsyncSession,
    transacciones: Sequence[Transaccion],
) -> set[str]:

    if not transacciones:
        return set()

    valores = [
        {
            "transaccion_id": transaccion.transaccion_id,
            "trace_id": transaccion.trace_id,
            "clave_idempotencia": transaccion.clave_idempotencia,
            "cuenta_origen_id": transaccion.cuenta_origen_id,
            "cuenta_destino_id": transaccion.cuenta_destino_id,
            "monto_centavos": transaccion.monto_centavos,
            "moneda": transaccion.moneda,
            "descripcion": transaccion.descripcion,
            "estado": transaccion.estado,
            "motivo": transaccion.motivo,
        }
        for transaccion in transacciones
    ]

    sentencia = (
        insert(Transaccion)
        .values(valores)
        ## permite ignorar conflictos tanto por transaccion_id
        ## como por clave_idempotencia sin abortar el lote completo
        .on_conflict_do_nothing()
        .returning(
            Transaccion.transaccion_id
        )
    )

    try:

        resultado = await sesion.execute(sentencia)
        ids_insertados = set(
            resultado.scalars().all()
        )

        for transaccion in transacciones:

            if (
                transaccion.transaccion_id
                not in ids_insertados
            ):
                continue

            await actualizar_saldos_transaccion(
                sesion=sesion,
                transaccion=transaccion,
            )

        ## todas las inserciones del lote se confirman juntas
        await sesion.commit()
        return ids_insertados

    except Exception:

        ## si cualquier error temporal afecta al lote completo
        ## ninguna transacción debe quedar parcialmente confirmada
        await sesion.rollback()

        raise
