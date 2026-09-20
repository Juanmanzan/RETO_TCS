from decimal import Decimal

from app.esquemas.recomendaciones import SolicitudRecomendacion
from app.repositorios.consulta import DatosCuentaCliente
from app.servicios.recomendaciones import generar_recomendacion


## test que verifica que la recomendacion conserva
## los datos principales de la transaccion
def test_generar_recomendacion_con_datos_cliente():

    solicitud = SolicitudRecomendacion(
        cuenta_origen_id=1001,
        monto_transferencia=Decimal("50.00"),
        transaccion_id="TRX-UNIT-IA",
        trace_id="trace-unit-ia",
    )

    datos = DatosCuentaCliente(
        cliente_id=1,
        cuenta_id=1001,
        ingresos_mensuales=Decimal("1800.00"),
        gastos_mensuales=Decimal("950.00"),
        saldo=Decimal("5000.00"),
    )

    resultado = generar_recomendacion(
        solicitud=solicitud,
        datos=datos,
    )

    assert resultado.id_usuario == 1
    assert resultado.transaccion_id == "TRX-UNIT-IA"
    assert resultado.trace_id == "trace-unit-ia"
    assert resultado.capacidad_financiera == "FAVORABLE"
    assert resultado.impacto_liquidez == "BAJO"
