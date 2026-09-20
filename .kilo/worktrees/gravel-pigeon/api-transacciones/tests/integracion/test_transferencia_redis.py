import requests

URL_API = "http://localhost:8002/api/transacciones"

## test que verifica que una transaccion se realiza de forma correcta 
## empleando el enpoind 
def test_transferencia_completada():

    datos = {
        "cuenta_origen_id": 1001,
        "cuenta_destino_id": 1002,
        "monto": 100.00,
        "moneda": "USD",
        "descripcion": "Pago de servicios",
        "clave_idempotencia": "test-integracion-001",
    }

    respuesta = requests.post(
        URL_API,
        json=datos,
        timeout=5,
    )

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["estado"] == "COMPLETADA"
    assert cuerpo["cuenta_origen_id"] == 1001
    assert cuerpo["cuenta_destino_id"] == 1002
    assert float(cuerpo["monto"]) == 100.0
    assert cuerpo["moneda"] == "USD"
    assert cuerpo["descripcion"] == "Pago de servicios"
    assert cuerpo["clave_idempotencia"] == "test-integracion-001"
    assert cuerpo["transaccion_id"].startswith("TRX-")


def test_transferencia_idempotente():
    datos = {
        "cuenta_origen_id": 1001,
        "cuenta_destino_id": 1002,
        "monto": 10.00,
        "moneda": "USD",
        "descripcion": "prueba idempotencia",
        "clave_idempotencia": "test-integracion-idempotencia-001",
    }

    primera = requests.post(
        URL_API,
        json=datos,
        timeout=5,
    )

    segunda = requests.post(
        URL_API,
        json=datos,
        timeout=5,
    )

    assert primera.status_code == 200
    assert segunda.status_code == 200

    cuerpo_1 = primera.json()
    cuerpo_2 = segunda.json()

    assert (
        cuerpo_1["transaccion_id"]
        == cuerpo_2["transaccion_id"]
    )


def test_transferencia_rechazada_por_fondos():
    datos = {
        "cuenta_origen_id": 1005,
        "cuenta_destino_id": 1001,
        "monto": 10000.00,
        "moneda": "USD",
        "descripcion": "prueba fondos insuficientes",
        "clave_idempotencia": "test-integracion-fondos-001",
    }

    respuesta = requests.post(
        URL_API,
        json=datos,
        timeout=5,
    )

    assert respuesta.status_code == 200

    cuerpo = respuesta.json()

    assert cuerpo["estado"] == "RECHAZADA"


def test_transferencia_rechazada_cuenta_inexistente():
    datos = {
        "cuenta_origen_id": 9999,
        "cuenta_destino_id": 1001,
        "monto": 10.00,
        "moneda": "USD",
        "descripcion": "prueba cuenta inexistente",
        "clave_idempotencia": "test-integracion-cuenta-001",
    }

    respuesta = requests.post(
        URL_API,
        json=datos,
        timeout=5,
    )

    assert respuesta.status_code == 200

    cuerpo = respuesta.json()

    assert cuerpo["estado"] == "RECHAZADA"
