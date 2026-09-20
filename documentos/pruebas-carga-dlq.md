# Pruebas de carga y DLQ

## Objetivo

Validar capacidad transaccional, latencia, errores y manejo de payloads invalidos.

## Instalacion de k6

PowerShell:

```powershell
winget install --id k6.k6 -e
k6 version
```

## Prueba de carga

Archivo:

```text
api-transacciones/tests/carga/carga_transacciones.js
```

Prueba minima:

```powershell
k6 run -e RATE=1 -e DURATION=5s api-transacciones/tests/carga/carga_transacciones.js
```

Prueba media:

```powershell
k6 run -e RATE=100 -e DURATION=30s api-transacciones/tests/carga/carga_transacciones.js
```

Prueba alta:

```powershell
k6 run -e RATE=2000 -e DURATION=60s api-transacciones/tests/carga/carga_transacciones.js
```

Si se necesita cambiar la URL:

```powershell
k6 run -e BASE_URL=http://localhost:8002 -e RATE=100 -e DURATION=30s api-transacciones/tests/carga/carga_transacciones.js
```

## Resultado local reportado

Completar con evidencia:

- TPS alcanzado: 2000 TPS
- Workers API: 4 workers Uvicorn
- CPU Docker: 4 cores
- Duracion prueba:
- p95:
- p99:
- tasa de error:
- captura Grafana:
- salida k6:

Nota para defensa: el resultado de 2000 TPS corresponde al entorno local usando los 4 cores disponibles en Docker. Para 10 000 TPS se plantearia escalar horizontalmente la API y workers, separar Redis/PostgreSQL en infraestructura dedicada, ajustar particionamiento y usar un broker administrado.

## Prueba de JSON envenenado / DLQ

El worker de persistencia captura errores permanentes de payload:

- JSON invalido
- UTF-8 invalido
- campos requeridos faltantes
- tipos incorrectos
- valores no convertibles

Cuando esto ocurre, publica el mensaje en:

```text
<MQTT_TOPIC_PERSISTENCIA>/dlq
```

### Publicar payload invalido

Usar los valores reales de `.env` si las variables no estan exportadas.

```powershell
docker exec mqtt_broker mosquitto_pub `
  -h localhost `
  -p 1883 `
  -u $env:MQTT_USER `
  -P $env:MQTT_PASSWORD `
  -t "smartbancs/transacciones/persistencia" `
  -q 1 `
  -m "{ json_invalido"
```

### Ver logs

```powershell
docker logs -f worker_persistencia
```

Se espera observar un log similar a:

```text
Evento MQTT invalido
Evento invalido enviado a DLQ
```

### Suscribirse a DLQ

```powershell
docker exec -it mqtt_broker mosquitto_sub `
  -h localhost `
  -p 1883 `
  -u $env:MQTT_USER `
  -P $env:MQTT_PASSWORD `
  -t "smartbancs/transacciones/persistencia/dlq" `
  -v
```

## Evidencias pendientes

- Captura k6.
- Captura Grafana.
- Captura de logs DLQ.
- Captura de VictoriaMetrics targets.
