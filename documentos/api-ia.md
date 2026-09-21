# Arquitectura de la API de IA

## Responsabilidad

Generar recomendaciones financieras personalizadas a partir de eventos de transferencia sin bloquear la respuesta de la API transaccional.

## Componentes

- `api-ia`: expone salud, metricas, endpoint interno de notificacion y WebSocket.
- `worker-ia`: consume eventos desde MQTT, construye solicitudes de recomendacion, consulta datos financieros, persiste la recomendacion y notifica a la UI.
- `servicios/recomendaciones.py`: contiene las reglas de clasificacion y construccion del mensaje.
- `repositorios`: consulta cuentas, clientes y persiste recomendaciones.

## Flujo

1. La transferencia genera un evento.
2. `worker-publicador` publica el evento en el topic MQTT de IA.
3. `worker-ia` consume el mensaje.
4. El worker transforma el evento en `SolicitudRecomendacion`.
5. Espera brevemente a que la transaccion exista en PostgreSQL, porque persistencia e IA trabajan en paralelo.
6. Consulta datos de cuenta y cliente.
7. Calcula capacidad financiera e impacto de liquidez.
8. Persiste la recomendacion si no existe.
9. Notifica a `api-ia`.
10. `api-ia` publica por WebSocket a la UI.

```mermaid
graph TD
    subgraph Evento["Origen del evento"]
        EVT["1. Evento de transferencia"]
        PUB["2. worker-publicador"]
        MQTT{{"Topic MQTT IA"}}
    end

    subgraph Consumo["Consumo y transformacion"]
        WIA["3. worker-ia consume mensaje"]
        DTO["4. Transforma a SolicitudRecomendacion"]
        WAIT["5. Espera existencia en PostgreSQL"]
    end

    subgraph Enriquecimiento["Enriquecimiento y calculo"]
        CONSULTA["6. Consulta cuenta y cliente"]
        CALC["7. Calcula capacidad e impacto"]
    end

    subgraph Persistencia["Persistencia"]
        PERSIST["8. Persiste recomendacion"]
        DB[("PostgreSQL")]
    end

    subgraph Notificacion["Notificacion a la UI"]
        NOTIFY["9. Notifica a api-ia"]
        APIIA["api-ia"]
        WS["10. Publica por WebSocket"]
        UI["UI"]
    end

    EVT --> PUB --> MQTT --> WIA --> DTO --> WAIT
    WAIT -->|"Consulta"| DB
    WAIT --> CONSULTA --> CALC --> PERSIST
    PERSIST -->|"Escribe"| DB
    PERSIST --> NOTIFY --> APIIA --> WS --> UI

    classDef api fill:#4A90D9,stroke:#2C5F8A,color:#fff,stroke-width:2px
    classDef worker fill:#5CB85C,stroke:#3D8B3D,color:#fff,stroke-width:2px
    classDef broker fill:#F0AD4E,stroke:#B8830E,color:#000,stroke-width:2px
    classDef db fill:#6C757D,stroke:#495057,color:#fff,stroke-width:2px
    classDef ui fill:#9B59B6,stroke:#6C3483,color:#fff,stroke-width:2px

    class APIIA api
    class PUB,WIA,DTO,WAIT,CONSULTA,CALC,PERSIST,NOTIFY worker
    class MQTT broker
    class DB db
    class EVT,WS,UI ui

    style Evento fill:#EAF2FA,stroke:#4A90D9,stroke-width:1px
    style Consumo fill:#EAFAEA,stroke:#5CB85C,stroke-width:1px
    style Enriquecimiento fill:#EAFAEA,stroke:#5CB85C,stroke-width:1px
    style Persistencia fill:#F0F0F0,stroke:#6C757D,stroke-width:1px
    style Notificacion fill:#F3EAF9,stroke:#9B59B6,stroke-width:1px
```

## Modelo de IA implementado en el MVP

El MVP usa un modelo basado en reglas de negocio, tomando en consideración que los datos financieros no pueden salir a red, por este motivo no se empleo ua API Key de una modelo Open Source:

- `capacidad_financiera`: compara gastos mensuales contra ingresos.
- `impacto_liquidez`: compara monto de transferencia contra saldo.
- `recomendacion`: texto generado segun la combinacion de ambos indicadores.

Clasificaciones:

- Capacidad financiera: `FAVORABLE`, `MODERADA`, `REDUCIDA`.
- Impacto de liquidez: `BAJO`, `MODERADO`, `ALTO`.

## Patrones de diseno y arquitectura usados

| Patron | Descripcion |
|---|---|
| Event-Driven Consumer | La IA se activa por eventos MQTT. |
| Worker Pattern | El procesamiento pesado vive fuera del request HTTP. |
| Service Layer | Las reglas se concentran en `servicios/recomendaciones.py`. |
| Repository Pattern | Consultas y persistencia estan separadas de las reglas. |
| DTO / Schema Pattern | Pydantic modela solicitudes, respuestas y notificaciones. |
| Backpressure basico | `worker-ia` usa una cola interna con limite y un semaforo de concurrencia. |
| Composition over Inheritance | Las funciones y servicios componen comportamiento sin jerarquias de clases innecesarias. |

## Por que no bloquea la transaccion

La API de transacciones no llama a IA de forma sincrona. Solo genera el evento. La recomendacion se produce despues, mediante MQTT y worker independiente. Si IA esta lenta o temporalmente caida, la transferencia puede responder igual.

```mermaid
graph LR
    API["api-transacciones<br/>Responde la transferencia<br/>de forma inmediata"]
    IA["worker-ia<br/>Genera la recomendacion<br/>en segundo plano"]

    API -.->|"Evento no bloqueante"| IA

    classDef sync fill:#4A90D9,stroke:#2C5F8A,color:#fff,stroke-width:2px
    classDef async fill:#5CB85C,stroke:#3D8B3D,color:#fff,stroke-width:2px
    class API sync
    class IA async
```