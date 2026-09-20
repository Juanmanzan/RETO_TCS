from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.esquemas.transacciones import TransferenciaRequest


## test que verifica que no se permita transferir
## hacia la misma cuenta de origen
def test_cuenta_origen_y_destino_no_pueden_ser_iguales():

    with pytest.raises(ValidationError):

        TransferenciaRequest(
            cuenta_origen_id=1001,
            cuenta_destino_id=1001,
            monto=Decimal("10.00"),
            moneda="USD",
            descripcion="prueba misma cuenta",
            clave_idempotencia="unit-cuentas-001",
        )
