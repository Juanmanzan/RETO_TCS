# SmartBancs App

El presente documento detalla el diseño arquitectónico y la implementación de un Producto Mínimo Viable (MVP) para un sistema de transferencias en tiempo real con generación de recomendaciones financieras asíncronas.

# Stack tecnológico empleado

**FastAPI:** Se emplea como framework principal de la solución, gracias a su gran rapidez en el procesamiento de peticiones, al estar construido sobre Starlette y Pydantic, adicional permite escalar tanto vertical como horizontalmente mediante múltiples workers.

**Redis:** Se emplea como base de datos transaccional en tiempo real, permite procesar la transacción en milisegundos. Esto aporta el rendimiento necesario para operaciones financieras que requieren baja latencia. Adicionalmente, mediante Redis Streams permite desacoplar la escritura de la transacción, a través de colas.

**PostgreSQL:** Se usa en la persistencia, encargada de almacenar de forma definitiva y consistente las transacciones generadas dentro del sistema. Se elige por su cumplimiento de propiedades ACID, además de contar con mecanismos maduros de control de acceso, auditoría y replicación.

**MQTT:** Se emplea como protocolo de mensajería ligero para la comunicación entre componentes que requieren eventos en tiempo real, dado su bajo overhead otorga un gran rendimiento en escenarios de alta frecuencia y su soporte de niveles de calidad de servicio (QoS) aportan confiabilidad en la entrega de la transacción.

**Workers asíncronos:** Se emplean procesos worker desacoplados del flujo principal de la API para el procesamiento de tareas que no requieren respuesta inmediata al usuario como: persistencia o generación de recomendaciones. Este enfoque permite que las transferencias se confirmen rápidamente sin bloquear al cliente por tareas secundarias.

**VictoriaMetrics:** Se emplea como motor de métricas para observabilidad del sistema, destacando por su bajo consumo de recursos y alto rendimiento en la ingesta y consulta de metricas.

**Grafana:** Se emplea como herramienta de visualización de métricas y dashboards, permitiendo monitorear el rendimiento del sistema: latencias, throughput, errores, lo cual facilita la detección temprana de cuellos de botella.

**Loki:** Se emplea como sistema de gestión centralizada de logs, permitiendo correlacionar eventos entre los distintos componentes del sistema: API, workers, base de datos de forma eficiente.

**k6:** Se emplea como herramienta de pruebas de carga, permitiendo simular múltiples usuarios concurrentes y validar el rendimiento del sistema bajo distintos escenarios de estrés.


## Arquitectura resumida

El flujo principal prioriza que la transferencia responda rapido y que los procesos secundarios trabajen por eventos:

```mermaid
graph TD
    subgraph Ingesta["Capa de Ingesta"]
        API["1. api-transacciones REST"]
        REDIS[("2. Redis Lua Scripts")]
    end

    subgraph Mensajeria["Capa de Mensajería"]
        STREAM[("3. Redis Stream")]
        PUB["4. worker-publicador"]
        MQTT{{"Broker MQTT"}}
    end

    subgraph Persistencia["Capa de Persistencia"]
        PERSIST["5. worker-persistencia"]
        DB[("PostgreSQL")]
        DLQ[("DLQ")]
    end

    subgraph IA["Capa de IA"]
        WIA["6. worker-ia"]
        APIIA["api-ia WebSocket"]
    end

    subgraph Obs["7. Observabilidad"]
        VM["VictoriaMetrics + vmagent"]
        GRAF["Grafana"]
        LOKI["Loki + Alloy"]
    end

    API -->|"Valida saldo e idempotencia"| REDIS
    REDIS -->|"Escribe evento"| STREAM
    STREAM --> PUB
    PUB --> MQTT

    MQTT --> PERSIST
    PERSIST -->|"Lotes"| DB
    PERSIST -.->|"Registros inválidos"| DLQ

    MQTT --> WIA
    WIA --> APIIA

    classDef api fill:#4A90D9,stroke:#2C5F8A,color:#fff,stroke-width:2px
    classDef cache fill:#D9534F,stroke:#A83F3C,color:#fff,stroke-width:2px
    classDef worker fill:#5CB85C,stroke:#3D8B3D,color:#fff,stroke-width:2px
    classDef broker fill:#F0AD4E,stroke:#B8830E,color:#000,stroke-width:2px
    classDef db fill:#6C757D,stroke:#495057,color:#fff,stroke-width:2px
    classDef obs fill:#9B59B6,stroke:#6C3483,color:#fff,stroke-width:2px

    class API,APIIA api
    class REDIS,STREAM cache
    class PUB,PERSIST,WIA worker
    class MQTT broker
    class DB,DLQ db
    class VM,GRAF,LOKI obs

    style Ingesta fill:#EAF2FA,stroke:#4A90D9,stroke-width:1px
    style Mensajeria fill:#FDF3E7,stroke:#F0AD4E,stroke-width:1px
    style Persistencia fill:#F0F0F0,stroke:#6C757D,stroke-width:1px
    style IA fill:#EAFAEA,stroke:#5CB85C,stroke-width:1px
    style Obs fill:#F3EAF9,stroke:#9B59B6,stroke-width:1px
```

Documentacion por tema:

- [Arquitectura general](documentos/arquitectura-general.md)
- [API de transacciones](documentos/api-transacciones.md)
- [API de IA](documentos/api-ia.md)
- [ETL](documentos/ETL.md)
- [Observabilidad y operacion](documentos/observabilidad-operacion.md)
- [Reto técnico teoría](documentos/respuestas-teoricas.md)
- [Declaración del uso de inteligencia artificial](documentos/declaratoria-del-uso-de-inteligencia-artificial.md)

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

1. Copiar el siguiente contenido dentro del archivo `.env.example`:

```dotenv
# base de datos 
POSTGRES_DB=RETO_TCS
POSTGRES_USER=TCS_ADMIN
POSTGRES_PASSWORD=okS27sgUcCkZpoytxyxQkqBLsFSiKzqu
POSTGRES_HOST=postgres
POSTGRES_PORT=5433
## usuario para las APIS de transacciones y IA
APP_DB_USER=app_user
APP_DB_PASSWORD=LHrtT9dveUbcMpJj3GQnhoxgXG5LQt2S
DATABASE_URL=postgresql+asyncpg://app_user:LHrtT9dveUbcMpJj3GQnhoxgXG5LQt2S@postgres:5432/RETO_TCS

# redis
REDIS_HOST=redis
REDIS_PORT=6380
REDIS_DB=0
REDIS_USER=app_user
REDIS_PASSWORD=AtE4D6DvFJ3QtLDRggeEUE6rrfVV2WMP
REDIS_URL=redis://app_user:AtE4D6DvFJ3QtLDRggeEUE6rrfVV2WMP@redis:6379/0
REDIS_MAX_CONNECTIONS=800
REDIS_STREAM_TRANSACCIONES=stream:transacciones
REDIS_CONSUMER_GROUP_MQTT=grupo:mqtt

# VICTORIAMETRICS
VICTORIAMETRICS_HOST=victoriametrics
VICTORIAMETRICS_PORT=8428

## servicio de mqtt

MQTT_HOST=mqtt
MQTT_PORT=1883
MQTT_USER=app_user
MQTT_PASSWORD=Y6sTsU6efofKA29RixgQc3ar7u2BEZUm
MQTT_URL=mqtt://app_user:Y6sTsU6efofKA29RixgQc3ar7u2BEZUm@mqtt:1883
MQTT_TOPIC_PERSISTENCIA=smartbancs/transacciones/persistencia
MQTT_TOPIC_IA=smartbancs/transacciones/ia

## grafana 

GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=3a1RwDX52qzpscqZA837RCTC3dCL22X3
```

2. Renombrar el archivo `.env.example` a `.env`:

```powershell
Copy-Item .env.example .env
```


## Ejecucion

Levantar toda la solucion construye e inicia todos los contenedores:

```powershell
# Levanta y construye los contenedores de la solucion
docker compose up -d --build
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

Reconstruir todo sin cache rebuild limpio de todas las imagenes:

```powershell
docker compose build --no-cache
docker compose up -d --force-recreate
```

Detener la solucion eliminando volumenes e imagenes, sin dejar cache de Docker:

```powershell
docker compose down -v --rmi all
docker builder prune -af
```

## Endpoints principales

- API transacciones: `http://localhost:8002`
- Swagger transacciones: `http://localhost:8002/docs`
- API IA: `http://localhost:8001`
- Swagger IA: `http://localhost:8001/docs`
- UI local: abrir `UI/index.html` en el navegador
- WebSocket recomendaciones: `ws://localhost:8001/ws/recomendaciones`

Ejemplo de payload para crear una transferencia (`POST /api/transacciones`):

```json
{
  "cuenta_origen_id": 1001,
  "cuenta_destino_id": 1002,
  "monto": 1,
  "moneda": "USD",
  "descripcion": "Pago de prueba",
  "clave_idempotencia": "manual-<uuid>"
}
```

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

### Pruebas de carga con k6

Prueba de carga simple:

```powershell
k6 run -e RATE=100 -e DURATION=5s api-transacciones/tests/carga/carga_transacciones.js
```

Prueba de carga media:

```powershell
k6 run -e RATE=500 -e DURATION=5000ms api-transacciones/tests/carga/carga_transacciones.js
```

Prueba de carga con mayor tasa:

```powershell
k6 run -e RATE=1000 -e DURATION=30s api-transacciones/tests/carga/carga_transacciones.js
```

Resultado alcanzado en la validacion local: aproximadamente 2000 TPS usando `api-transacciones` con 4 workers de Uvicorn y los 4 cores disponibles en Docker Desktop. En una prueba sintetica controlada, con tiempos de respuesta menores a 2 segundos.


## Estructura del repositorio

| Carpeta | Contenido |
|---|---|
| `api-transacciones/` | API REST, dominio transaccional, Redis Lua, workers y pruebas |
| `api-ia/` | API de IA, reglas de recomendacion, WebSocket, worker IA y pruebas |
| `postgres/init/` | DDL, DML y permisos iniciales |
| `redis/init/` | Inicializacion de saldos/cuentas en Redis |
| `mqtt/config/` | Configuracion del broker Mosquitto |
| `observabilidad/` | Configuracion de vmagent y Alloy |
| `grafana/` | Datasources y dashboards |
| `ETL/` | Proceso de transformacion de datos |
| `UI/` | Interfaz local para probar transferencias y recomendaciones |
| `documentos/` | Documentacion tecnica por dominio |

## Declaracion de uso de IA

Completar antes de la entrega:

- Herramientas usadas:
- Componentes donde se uso IA:
- Actividades apoyadas por IA:
- Validaciones realizadas por el autor:
