from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.esquemas.transacciones import TransferenciaRequest


## test que verifica que no se pueda enviar menos de un centavo
def test_monto_menor_a_un_centavo_es_invalido():

    with pytest.raises(ValidationError):

        TransferenciaRequest(
            cuenta_origen_id=1001,
            cuenta_destino_id=1002,
            monto=Decimal("0.001"),
            moneda="USD",
            descripcion="monto menor a un centavo",
            clave_idempotencia="unit-monto-minimo-001",
        )
