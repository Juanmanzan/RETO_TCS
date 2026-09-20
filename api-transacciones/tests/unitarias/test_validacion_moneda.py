from decimal import Decimal

from app.esquemas.transacciones import TransferenciaRequest


## test que verifica que la moneda se normaliza a mayusculas
## cuando el cliente envia usd
def test_moneda_usd_se_convierte_a_mayusculas():

    transferencia = TransferenciaRequest(
        cuenta_origen_id=1001,
        cuenta_destino_id=1002,
        monto=Decimal("10.00"),
        moneda="usd",
        descripcion="prueba moneda",
        clave_idempotencia="unit-moneda-001",
    )

    assert transferencia.moneda == "USD"
