from decimal import Decimal

from app.servicios.recomendaciones import (
    clasificar_capacidad_financiera,
)


## test que verifica que el cliente tenga capacidad reducida
## cuando sus gastos consumen casi todo el ingreso
def test_capacidad_financiera_reducida():

    resultado = clasificar_capacidad_financiera(
        ingresos_mensuales=Decimal("1200.00"),
        gastos_mensuales=Decimal("1050.00"),
    )

    assert resultado == "REDUCIDA"
