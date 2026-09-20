import requests


URL_API = "http://localhost:8001/recomendaciones/simular"


## test que verifica que la recomendacion manual ya no sea publica.
## las recomendaciones deben generarse desde los eventos del worker.
def test_recomendacion_simulada_no_expuesta():

    datos = {
        "cuenta_origen_id": 1001,
        "monto_transferencia": 25.00,
        "transaccion_id": "TRX-TEST-IA-ENDPOINT",
        "trace_id": "trace-test-ia-endpoint",
    }

    respuesta = requests.post(
        URL_API,
        json=datos,
        timeout=5,
    )

    assert respuesta.status_code == 404
