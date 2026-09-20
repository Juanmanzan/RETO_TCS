from decimal import Decimal

from app.core.transacciones.montos import convertir_a_centavos


## test que verifica que el monto decimal se guarde en centavos
## para no perder precision financiera
def test_convertir_monto_a_centavos():

    resultado = convertir_a_centavos(
        Decimal("10.25")
    )

    assert resultado == 1025
