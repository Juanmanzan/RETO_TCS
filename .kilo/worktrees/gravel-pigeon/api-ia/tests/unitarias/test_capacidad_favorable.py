from decimal import Decimal

from app.servicios.recomendaciones import (
    clasificar_capacidad_financiera,
)


## test que verifica que el cliente tenga capacidad favorable
## cuando sus gastos son bajos frente a sus ingresos
def test_capacidad_financiera_favorable():

    resultado = clasificar_capacidad_financiera(
        ingresos_mensuales=Decimal("1800.00"),
        gastos_mensuales=Decimal("950.00"),
    )

    assert resultado == "FAVORABLE"
