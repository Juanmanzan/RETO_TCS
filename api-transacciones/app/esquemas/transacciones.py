from datetime import datetime
from decimal import Decimal
from enum import Enum
from pydantic import BaseModel, Field, field_validator
from pydantic import ValidationInfo

## validacion del enum de los estados de una transaccion completada, rechazada 
class EstadoTransaccion(str, Enum):
    COMPLETADA = "COMPLETADA"
    RECHAZADA = "RECHAZADA"


## validacion del contrato de entrada (request) antes de ser procesada 
class TransferenciaRequest(BaseModel):
    cuenta_origen_id: int = Field(gt=0) ## debe ser mayor a 0 y entero
    cuenta_destino_id: int = Field(gt=0)## debe ser mayor a 0 y entero 
    monto: Decimal = Field(ge=Decimal("0.01")) ## debe ser minimo de un centavo
    moneda: str = Field(min_length=3,max_length=3,) ## el string debe tener una longitud minima y maxima de 3 caracteres 
    descripcion: str = Field(max_length=255,) ## la descripcion debe ser un string de maximo 255 caracteres 
    clave_idempotencia: str = Field(min_length=1,max_length=64,) ## la key de idempotencia debe ser un string con un maximo de 64 caracteres  
    ## validacion personalizada del tipo de moneda 
    ## para el reto tecnico se va a manejar dolares
    @field_validator("moneda")
    @classmethod
    def validar_moneda(cls, moneda: str) -> str:
        moneda = moneda.upper()
        if moneda != "USD":
            raise ValueError(
                "solo se admite la moneda USD"
            )
        return moneda
    ##validacion personalizada que garantiza que una transaccion se realiza entre dos cuentas diferentes 
    @field_validator("cuenta_destino_id")
    @classmethod
    def validar_cuenta_destino(
        cls,
        cuenta_destino_id: int,
        info: ValidationInfo,
    ) -> int:
        cuenta_origen_id = info.data.get("cuenta_origen_id")
        if (cuenta_destino_id == cuenta_origen_id):
            raise ValueError(
                "la cuenta de origen y destino deben ser diferentes"
            )

        return cuenta_destino_id

## contrato de respuesta de la api de transsacciones 
class TransferenciaResponse(BaseModel):
    transaccion_id: str
    estado: EstadoTransaccion
    motivo: str
    cuenta_origen_id: int
    cuenta_destino_id: int
    monto: Decimal
    moneda: str
    descripcion: str
    clave_idempotencia: str
