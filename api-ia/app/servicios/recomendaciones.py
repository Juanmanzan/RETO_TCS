import asyncio
from decimal import Decimal
from time import perf_counter

from app.esquemas.recomendaciones import (
    RespuestaRecomendacion,
    SolicitudRecomendacion,
)
from app.infraestructura.observabilidad.metricas import (
    DURACION_RECOMENDACION,
    RECOMENDACIONES_PROCESADAS_TOTAL,
    RECOMENDACIONES_SOLICITADAS_TOTAL,
)
from app.infraestructura.postgres.conexion import SesionPostgresql
from app.repositorios.consulta import (
    DatosCuentaCliente,
    existe_recomendacion,
    existe_transaccion,
    obtener_datos_cuenta_cliente,
)
from app.repositorios.persistencia import (
    ResultadoPersistenciaRecomendacion,
    insertar_recomendacion,
)


class CuentaNoEncontradaError(Exception):
    pass


class TransaccionNoDisponibleError(Exception):
    pass


## calcula la capacidad financiera usando reglas simples
def clasificar_capacidad_financiera(
    ingresos_mensuales: Decimal,
    gastos_mensuales: Decimal,
) -> str:

    if ingresos_mensuales <= 0:
        return "REDUCIDA"

    porcentaje_gastos = (
        gastos_mensuales
        / ingresos_mensuales
    )

    if porcentaje_gastos <= Decimal("0.60"):
        return "FAVORABLE"

    if porcentaje_gastos <= Decimal("0.80"):
        return "MODERADA"

    return "REDUCIDA"


## calcula cuanto afecta la transferencia al saldo actual
def clasificar_impacto_liquidez(
    saldo_actual: Decimal,
    monto_transferencia: Decimal,
) -> str:

    if saldo_actual <= 0:
        return "ALTO"

    impacto = (
        monto_transferencia
        / saldo_actual
    )

    if impacto <= Decimal("0.30"):
        return "BAJO"

    if impacto <= Decimal("0.60"):
        return "MODERADO"

    return "ALTO"


## arma una recomendacion corta segun los indicadores calculados
def construir_mensaje_recomendacion(
    capacidad_financiera: str,
    impacto_liquidez: str,
) -> str:

    if (
        capacidad_financiera == "FAVORABLE"
        and impacto_liquidez == "BAJO"
    ):
        return (
            "Vas por buen camino. Mantienes un margen financiero "
            "favorable y esta operacion conserva buena liquidez. "
            "Podrias destinar parte de tu disponibilidad a una meta "
            "de ahorro."
        )

    if impacto_liquidez == "ALTO":
        return (
            "Esta operacion representa una parte importante de tu "
            "saldo actual. Conviene mantener una reserva para tus "
            "proximos compromisos antes de mover montos similares."
        )

    if capacidad_financiera == "REDUCIDA":
        return (
            "Tu margen mensual luce ajustado. Te recomendamos "
            "priorizar compromisos cercanos y revisar tus gastos "
            "antes de crear una nueva meta de ahorro."
        )

    return (
        "Tu situacion permite organizar la operacion con cautela. "
        "Revisa tus proximos pagos y define una meta de ahorro que "
        "no afecte tu liquidez."
    )


## genera la recomendacion con la informacion de cuenta y cliente
def generar_recomendacion(
    solicitud: SolicitudRecomendacion,
    datos: DatosCuentaCliente,
) -> RespuestaRecomendacion:

    capacidad_financiera = clasificar_capacidad_financiera(
        ingresos_mensuales=datos.ingresos_mensuales,
        gastos_mensuales=datos.gastos_mensuales,
    )

    impacto_liquidez = clasificar_impacto_liquidez(
        saldo_actual=datos.saldo,
        monto_transferencia=solicitud.monto_transferencia,
    )

    recomendacion = construir_mensaje_recomendacion(
        capacidad_financiera=capacidad_financiera,
        impacto_liquidez=impacto_liquidez,
    )

    return RespuestaRecomendacion(
        id_usuario=datos.cliente_id,
        cuenta_origen_id=datos.cuenta_id,
        transaccion_id=solicitud.transaccion_id,
        trace_id=solicitud.trace_id,
        capacidad_financiera=capacidad_financiera,
        impacto_liquidez=impacto_liquidez,
        recomendacion=recomendacion,
    )


## flujo usado por el endpoint para probar la ia de forma directa
async def simular_recomendacion(
    solicitud: SolicitudRecomendacion,
) -> RespuestaRecomendacion:

    inicio = perf_counter()

    RECOMENDACIONES_SOLICITADAS_TOTAL.labels(
        origen="endpoint",
    ).inc()

    async with SesionPostgresql() as sesion:

        datos = await obtener_datos_cuenta_cliente(
            sesion=sesion,
            cuenta_origen_id=solicitud.cuenta_origen_id,
        )

    if datos is None:
        raise CuentaNoEncontradaError(
            "cuenta origen no encontrada"
        )

    recomendacion = generar_recomendacion(
        solicitud=solicitud,
        datos=datos,
    )

    RECOMENDACIONES_PROCESADAS_TOTAL.labels(
        origen="endpoint",
        capacidad_financiera=(
            recomendacion.capacidad_financiera
        ),
        impacto_liquidez=recomendacion.impacto_liquidez,
    ).inc()

    DURACION_RECOMENDACION.observe(
        perf_counter() - inicio
    )

    return recomendacion


## espera a que la transaccion exista en postgres
## porque persistencia e ia trabajan en paralelo
async def esperar_transaccion_disponible(
    transaccion_id: str,
    intentos: int = 20,
    espera_segundos: float = 0.10,
) -> None:

    for _ in range(intentos):

        async with SesionPostgresql() as sesion:

            existe = await existe_transaccion(
                sesion=sesion,
                transaccion_id=transaccion_id,
            )

        if existe:
            return

        await asyncio.sleep(
            espera_segundos
        )

    raise TransaccionNoDisponibleError(
        "transaccion aun no esta disponible en postgres"
    )


## flujo usado por el worker para generar y persistir la respuesta
async def procesar_recomendacion_worker(
    solicitud: SolicitudRecomendacion,
) -> tuple[
    RespuestaRecomendacion,
    ResultadoPersistenciaRecomendacion,
]:

    inicio = perf_counter()

    RECOMENDACIONES_SOLICITADAS_TOTAL.labels(
        origen="worker",
    ).inc()

    if solicitud.transaccion_id:

        await esperar_transaccion_disponible(
            solicitud.transaccion_id
        )

    async with SesionPostgresql() as sesion:

        datos = await obtener_datos_cuenta_cliente(
            sesion=sesion,
            cuenta_origen_id=solicitud.cuenta_origen_id,
        )

        if datos is None:
            raise CuentaNoEncontradaError(
                "cuenta origen no encontrada"
            )

        recomendacion = generar_recomendacion(
            solicitud=solicitud,
            datos=datos,
        )

        if (
            solicitud.transaccion_id
            and await existe_recomendacion(
                sesion=sesion,
                transaccion_id=solicitud.transaccion_id,
            )
        ):
            return (
                recomendacion,
                ResultadoPersistenciaRecomendacion(
                    recomendacion_id=None,
                    insertada=False,
                ),
            )

        resultado_persistencia = await insertar_recomendacion(
            sesion=sesion,
            recomendacion=recomendacion,
        )

    RECOMENDACIONES_PROCESADAS_TOTAL.labels(
        origen="worker",
        capacidad_financiera=(
            recomendacion.capacidad_financiera
        ),
        impacto_liquidez=recomendacion.impacto_liquidez,
    ).inc()

    DURACION_RECOMENDACION.observe(
        perf_counter() - inicio
    )

    return (
        recomendacion,
        resultado_persistencia,
    )
