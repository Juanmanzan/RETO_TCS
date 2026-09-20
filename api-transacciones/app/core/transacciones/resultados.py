from dataclasses import dataclass

## DTO inmutable para estructurar la respuesta que viene de lua 
@dataclass(frozen=True)
class ResultadoTransferencia:
    tipo_resultado: str
    transaccion_id: str
    estado: str
    motivo: str

## funcion que convierte la respuesta de lua en un resultado mas legible por el
## servicio de transacciones
## mapea los resultados obtenidos a un contrado establecido ResultadoTransferencia 
def interpretar_resultado_redis(
    resultado: list,
) -> ResultadoTransferencia:

    if not resultado or len(resultado) < 4:
        raise ValueError(
            "respuesta invalida recibida desde redis"
        )

    return ResultadoTransferencia(
        tipo_resultado=resultado[0],
        transaccion_id=resultado[1],
        estado=resultado[2],
        motivo=resultado[3],
    )