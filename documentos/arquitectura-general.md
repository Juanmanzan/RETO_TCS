# Arquitectura general

## Objetivo

SmartBancs App busca procesar transferencias en tiempo real y generar recomendaciones financieras sin bloquear el flujo transaccional principal.

## Vista de alto nivel

```text
Cliente / UI
    |
    v
api-transacciones
    |
    v
Redis + Lua atomico
    |
    v
Redis Stream
    |
    v
worker-publicador
    |
    v
MQTT
    |-----------------------------|
    v                             v
worker-persistencia          worker-ia
    |                             |
    v                             v
PostgreSQL                  api-ia + PostgreSQL
                                  |
                                  v
                              WebSocket UI
```

## Componentes

- `api-transacciones`: recibe transferencias, valida contrato, ejecuta el procesamiento atomico en Redis y responde el comprobante.
- `Redis`: mantiene saldos operativos de baja latencia, claves de idempotencia y Redis Stream para desacoplar el procesamiento posterior.
- `worker-publicador`: lee Redis Stream y publica eventos hacia MQTT.
- `MQTT`: bus liviano de eventos para persistencia e IA.
- `worker-persistencia`: persiste transacciones en PostgreSQL por lotes; maneja duplicados y DLQ.
- `PostgreSQL`: repositorio duradero para transacciones, clientes, cuentas y recomendaciones.
- `api-ia`: expone endpoints de salud, metricas y WebSocket para recomendaciones.
- `worker-ia`: consume eventos de transferencia y genera recomendaciones con reglas de negocio.
- `VictoriaMetrics/Grafana/Loki/Alloy`: metricas, dashboards y logs centralizados.

## Decisiones de arquitectura

### Modelo principal

Se usa una arquitectura de microservicios livianos orientada a eventos. La API de transacciones no espera a que PostgreSQL ni IA finalicen para responder; solo confirma que la operacion atomica en Redis termino.

### Separacion por capas

Los servicios estan organizados en capas:

- `rutas`: contrato HTTP.
- `esquemas`: validacion de entrada/salida con Pydantic.
- `servicios`: casos de uso.
- `core`: reglas puras de dominio.
- `repositorios`: acceso a datos.
- `infraestructura`: Redis, PostgreSQL, MQTT, metricas y logs.
- `workers`: procesamiento asincrono.

### Patrones usados

- Layered Architecture: separa rutas, servicios, dominio, repositorios e infraestructura.
- Event-Driven Architecture: Redis Stream y MQTT desacoplan persistencia e IA.
- Producer/Consumer: API produce eventos; workers los consumen.
- Transactional Outbox simplificado: la operacion atomica en Redis escribe el evento en Redis Stream como parte del mismo script Lua.
- Repository Pattern: encapsula consultas e inserciones de PostgreSQL.
- Dependency Injection: FastAPI inyecta el servicio de transacciones inicializado en `lifespan`.
- Idempotency Key Pattern: evita procesar dos veces la misma transferencia.
- DLQ Pattern: payloads invalidos se envian a una cola de errores para analisis.

## Concurrencia y consistencia

La concurrencia critica se resuelve en Redis mediante un script Lua. Redis ejecuta scripts de forma atomica, por lo que la validacion de saldo, el debito, el credito, la idempotencia y la creacion del evento ocurren como una sola unidad logica.

PostgreSQL queda como almacenamiento duradero y defensa adicional contra duplicados. La persistencia se realiza por lotes para reducir overhead durante picos de carga.

## Escalabilidad

- `api-transacciones` corre con 4 workers de Uvicorn.
- Los workers se pueden escalar horizontalmente porque consumen por grupos/colas.
- MQTT permite desacoplar consumidores por dominio.
- Redis absorbe el camino caliente de la transferencia.
- PostgreSQL recibe escrituras por lotes desde workers, no una escritura directa por cada request HTTP.

## Tolerancia a fallos

- Si MQTT falla, el evento sigue pendiente en Redis Stream hasta poder publicarse.
- Si PostgreSQL falla, el worker de persistencia no confirma el mensaje y evita perdida de datos.
- Si un payload esta corrupto, se envia a DLQ antes de confirmar el mensaje original.
- La idempotencia reduce efectos por reintentos del cliente.

## Pendiente para completar

- Diagrama final para la presentacion.
- Evidencia de prueba de carga.
- Comparacion teorica contra la meta de 10 000 TPS.
- Supuestos de infraestructura productiva.
