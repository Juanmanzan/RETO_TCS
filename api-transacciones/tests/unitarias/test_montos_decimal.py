from decimal import Decimal

from app.core.transacciones.montos import convertir_a_decimal


## test que verifica que los centavos vuelvan al monto decimal
## usado en la respuesta de la api
def test_convertir_centavos_a_decimal():

    resultado = convertir_a_decimal(
        12345
    )

    assert resultado == Decimal("123.45")
