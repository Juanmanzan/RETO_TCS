from decimal import Decimal, ROUND_HALF_UP

## convierte un monto decimal a centavos para oibtener precision financiera 
def convertir_a_centavos(monto: Decimal) -> int:

    monto_normalizado = monto.quantize(Decimal("0.01"),rounding=ROUND_HALF_UP,)
    return int(monto_normalizado * 100)

## convierte un moto expresado en centavos a decimal 
def convertir_a_decimal(centavos: int) -> Decimal:
    return Decimal(centavos) / Decimal(100)