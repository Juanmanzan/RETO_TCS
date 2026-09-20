# SmartBancs App - Reto Tecnico TCS

MVP de una plataforma financiera para procesar transferencias en tiempo real y generar recomendaciones financieras no bloqueantes con un servicio de IA. La solucion usa FastAPI, Redis, PostgreSQL, MQTT, workers asincronos, observabilidad con VictoriaMetrics/Grafana/Loki y pruebas de carga con k6.

## Arquitectura resumida

El flujo principal prioriza que la transferencia responda rapido y que los procesos secundarios trabajen por eventos:

1. `api-transacciones` recibe la solicitud REST.
2. Redis ejecuta un script Lua atomico para validar cuentas, saldo, idempotencia y movimiento de saldos.
3. El resultado queda en Redis Stream y la API responde el comprobante con `transaccion_id`, `estado`, `motivo`, cuentas, monto, moneda, descripcion y `clave_idempotencia`.
4. `worker-publicador` consume Redis Stream y publica el evento en MQTT.
5. `worker-persistencia` consume MQTT, persiste lotes en PostgreSQL y manda payloads invalidos a DLQ.
6. `worker-ia` consume el evento, genera una recomendacion financiera, la persiste y la publica por WebSocket mediante `api-ia`.
7. VictoriaMetrics, vmagent, Grafana, Loki y Alloy exponen metricas y logs para diagnostico.

Documentacion por tema:

- [Arquitectura general](documentos/arquitectura-general.md)
- [API de transacciones](documentos/api-transacciones.md)
- [API de IA](documentos/api-ia.md)
- [Integracion Bancs y ETL](documentos/bancs-etl.md)
- [Observabilidad y operacion](documentos/observabilidad-operacion.md)
- [Pruebas de carga y DLQ](documentos/pruebas-carga-dlq.md)
- [Respuestas teoricas pendientes](documentos/respuestas-teoricas.md)

## Prerrequisitos

- Docker Desktop
- Docker Compose
- PowerShell
- Python 3.12, solo si se ejecutan pruebas locales fuera de Docker
- k6 para pruebas de carga

Instalar k6 en PowerShell:

```powershell
winget install --id k6.k6 -e
```

Verificar:

```powershell
k6 version
```

## Configuracion

1. Crear el archivo `.env` desde el ejemplo:

```powershell
Copy-Item .env.example .env
```

2. Completar las variables de PostgreSQL, Redis, MQTT y Grafana. Si ya existe un `.env` local en el equipo, conservarlo.

Variables importantes usadas por Docker Compose:

- `DATABASE_URL`
- `REDIS_URL`
- `REDIS_STREAM_TRANSACCIONES`
- `REDIS_CONSUMER_GROUP_MQTT`
- `MQTT_URL`
- `MQTT_TOPIC_PERSISTENCIA`
- `MQTT_TOPIC_IA`
- `GRAFANA_ADMIN_USER`
- `GRAFANA_ADMIN_PASSWORD`

## Ejecucion

Levantar toda la solucion:

```powershell
docker compose up -d --build
```

Reconstruir solo la API de transacciones:

```powershell
docker compose up -d --build --force-recreate api-transacciones
```

Ver estado de contenedores:

```powershell
docker compose ps
```

Detener la solucion:

```powershell
docker compose down
```

Detener y eliminar volumenes de datos:

```powershell
docker compose down -v
```

## Endpoints principales

- API transacciones: `http://localhost:8002`
- Swagger transacciones: `http://localhost:8002/docs`
- API IA: `http://localhost:8001`
- Swagger IA: `http://localhost:8001/docs`
- UI local: abrir `UI/index.html` en el navegador
- WebSocket recomendaciones: `ws://localhost:8001/ws/recomendaciones`

Crear una transferencia desde PowerShell:

```powershell
$body = @{
  cuenta_origen_id = 1001
  cuenta_destino_id = 1002
  monto = 1
  moneda = "USD"
  descripcion = "Pago de prueba"
  clave_idempotencia = "manual-$([guid]::NewGuid())"
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8002/api/transacciones" `
  -ContentType "application/json" `
  -Body $body
```

La respuesta funciona como comprobante de la operacion e incluye el campo `motivo`. Ejemplos de motivo: `OK`, `FONDOS_INSUFICIENTES`, `CUENTA_ORIGEN_NO_EXISTE`, `CUENTA_DESTINO_NO_EXISTE`, `MONTO_INVALIDO`.

## Logs utiles

Ver logs de la API de transacciones:

```powershell
docker logs -f api_transacciones
```

Ver logs del worker publicador:

```powershell
docker logs -f worker_publicador_eventos
```

Ver logs del worker de persistencia:

```powershell
docker logs -f worker_persistencia
```

Ver logs del worker de IA:

```powershell
docker logs -f worker_ia
```

## Observabilidad

- Targets de vmagent: `http://localhost:8430/targets`
- VictoriaMetrics VMUI: `http://localhost:8429/vmui`
- Grafana: `http://localhost:3000/`

Dashboards provisionados:

- Metricas de aplicacion: `grafana/dashboards/metricas-app.json`
- Logs de aplicacion: `grafana/dashboards/logs-app.json`

## Pruebas

Pruebas unitarias e integracion de transacciones:

```powershell
docker compose run --rm api-transacciones pytest
```

Pruebas unitarias e integracion de IA:

```powershell
docker compose run --rm api-ia pytest
```

Prueba de carga simple con k6:

```powershell
k6 run -e RATE=1 -e DURATION=5s api-transacciones/tests/carga/carga_transacciones.js
```

Prueba de carga con mayor tasa:

```powershell
k6 run -e RATE=100 -e DURATION=30s api-transacciones/tests/carga/carga_transacciones.js
```

Resultado alcanzado en la validacion local: aproximadamente 2000 TPS usando `api-transacciones` con 4 workers de Uvicorn y los 4 cores disponibles en Docker Desktop. Ver detalle y espacio para evidencias en [pruebas-carga-dlq.md](documentos/pruebas-carga-dlq.md).

## Prueba de JSON envenenado / DLQ

Enviar un payload invalido al topic de persistencia:

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

Si las variables no estan exportadas en PowerShell, reemplazar usuario, password y topic por los valores definidos en `.env`.

Validar que el worker envie el mensaje a DLQ:

```powershell
docker logs -f worker_persistencia
```

## Estructura del repositorio

```text
api-transacciones/   API REST, dominio transaccional, Redis Lua, workers y pruebas
api-ia/              API de IA, reglas de recomendacion, WebSocket, worker IA y pruebas
postgres/init/       DDL, DML y permisos iniciales
redis/init/          Inicializacion de saldos/cuentas en Redis
mqtt/config/         Configuracion del broker Mosquitto
observabilidad/      Configuracion de vmagent y Alloy
grafana/             Datasources y dashboards
ETL/                 Proceso de transformacion de datos
UI/                  Interfaz local para probar transferencias y recomendaciones
documentos/          Documentacion tecnica por dominio
```

## Declaracion de uso de IA

Completar antes de la entrega:

- Herramientas usadas:
- Componentes donde se uso IA:
- Actividades apoyadas por IA:
- Validaciones realizadas por el autor:
