from decimal import Decimal

from app.servicios.recomendaciones import (
    clasificar_impacto_liquidez,
)


## test que verifica el impacto moderado de una transferencia
## sobre el saldo disponible
def test_impacto_liquidez_moderado():

    resultado = clasificar_impacto_liquidez(
        saldo_actual=Decimal("1000.00"),
        monto_transferencia=Decimal("400.00"),
    )

    assert resultado == "MODERADO"
