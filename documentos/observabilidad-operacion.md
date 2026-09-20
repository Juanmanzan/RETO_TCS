# Observabilidad y operacion

## Objetivo

Definir que informacion permite identificar problemas de rendimiento, degradacion, timeouts, errores y bloqueos durante picos transaccionales.

## Stack implementado

- Prometheus client en APIs y workers.
- vmagent para recolectar metricas.
- VictoriaMetrics como almacenamiento de metricas.
- Grafana para dashboards.
- Loki para logs.
- Alloy para recolectar logs de contenedores.

## URLs

- Targets de vmagent: `http://localhost:8430/targets`
- VictoriaMetrics VMUI: `http://localhost:8429/vmui`
- Grafana: `http://localhost:3000/`

## Senales usadas

### Metricas

- volumen de transacciones por segundo
- transacciones por estado
- transacciones por motivo
- latencia HTTP de la API
- duracion del script Lua
- eventos publicados a MQTT
- errores MQTT
- eventos persistidos
- eventos duplicados
- eventos enviados a DLQ
- recomendaciones procesadas
- errores de IA

### Logs

Los logs incluyen campos para trazabilidad:

- `trace_id`
- `transaccion_id`
- `estado`
- `motivo`
- `clave_idempotencia`
- componente
- evento
- duracion

### Trazabilidad

El mismo `trace_id` viaja desde la API de transacciones hacia Redis Stream, MQTT, persistencia e IA. Esto permite buscar una transferencia especifica entre componentes.

## Diagnostico del incidente simulado

Escenario: en quincena, las transferencias no se completan; hay latencia alta, timeouts con base de datos y posibles deadlocks.

### Que revisar primero

1. Grafana: latencia p95/p99 de `api-transacciones`.
2. Grafana: errores por componente.
3. Logs de `api_transacciones` buscando `trace_id` o excepciones.
4. Logs de `worker_persistencia` buscando errores temporales de PostgreSQL.
5. Metricas de eventos pendientes o no confirmados.
6. PostgreSQL: conexiones activas, consultas lentas y bloqueos.

### Comandos utiles

```powershell
docker logs -f api_transacciones
docker logs -f worker_publicador_eventos
docker logs -f worker_persistencia
docker logs -f worker_ia
docker compose ps
```

Entrar a PostgreSQL:

```powershell
docker exec -it postgres_transacciones psql -U $env:POSTGRES_USER -d $env:POSTGRES_DB
```

Consulta sugerida para bloqueos en PostgreSQL:

```sql
SELECT
  blocked.pid AS blocked_pid,
  blocked.query AS blocked_query,
  blocking.pid AS blocking_pid,
  blocking.query AS blocking_query
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked
  ON blocked.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks
  ON blocking_locks.locktype = blocked_locks.locktype
 AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
 AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
 AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
 AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
 AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
 AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
 AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
 AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
 AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
 AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking
  ON blocking.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
```

## Acciones inmediatas ante incidente

Completar con tu respuesta final. Base sugerida:

- Aumentar temporalmente replicas/workers de consumidores si el cuello esta en workers.
- Reducir tasa de entrada con rate limit si la base esta saturada.
- Pausar consumidores secundarios no criticos, por ejemplo IA, para priorizar transferencias.
- Finalizar sesiones bloqueantes identificadas en PostgreSQL.
- Aumentar pool/timeout solo si la base tiene capacidad real.
- Revisar consultas lentas e indices.
- Activar modo degradado: transferencias primero, recomendaciones despues.

## Post mortem

Completar:

- Resumen ejecutivo:
- Impacto:
- Linea de tiempo:
- Causa raiz:
- Factores contribuyentes:
- Deteccion:
- Respuesta:
- Que funciono:
- Que no funciono:
- Acciones preventivas de infraestructura:
- Acciones preventivas de codigo:
- Owner y fecha compromiso:
