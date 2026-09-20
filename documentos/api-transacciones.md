# Arquitectura de la API de transacciones

## Responsabilidad

Procesar solicitudes de transferencia con baja latencia, validando el contrato, ejecutando la operacion atomica de saldo e iniciando el flujo asincrono de persistencia e IA.

## Endpoint principal

```http
POST /api/transacciones
```

Contrato de entrada:

```json
{
  "cuenta_origen_id": 1001,
  "cuenta_destino_id": 1002,
  "monto": 1,
  "moneda": "USD",
  "descripcion": "Pago de prueba",
  "clave_idempotencia": "abc-123"
}
```

Comprobante de salida:

```json
{
  "transaccion_id": "TX-...",
  "estado": "COMPLETADA",
  "motivo": "OK",
  "cuenta_origen_id": 1001,
  "cuenta_destino_id": 1002,
  "monto": 1,
  "moneda": "USD",
  "descripcion": "Pago de prueba",
  "clave_idempotencia": "abc-123"
}
```

El campo `motivo` se incluye para explicar el resultado de negocio del comprobante: `OK`, `FONDOS_INSUFICIENTES`, `CUENTA_ORIGEN_NO_EXISTE`, `CUENTA_DESTINO_NO_EXISTE`, `MONTO_INVALIDO`, entre otros.

## Flujo interno

1. `rutas/transacciones.py` recibe la solicitud HTTP.
2. Pydantic valida cuentas, monto minimo, moneda `USD`, descripcion y clave de idempotencia.
3. `ServicioTransacciones` genera `transaccion_id` y `trace_id`.
4. Convierte el monto a centavos para evitar errores de coma flotante.
5. Ejecuta `transferencia.lua` en Redis.
6. Redis valida idempotencia, existencia de cuentas y saldo.
7. Redis descuenta y acredita saldos.
8. Redis escribe el evento en `Redis Stream`.
9. La API responde el comprobante.
10. Los workers continuan persistencia e IA fuera del request HTTP.

## Patrones de diseno y arquitectura usados

- Service Layer: `ServicioTransacciones` concentra el caso de uso.
- Dependency Injection: la ruta recibe el servicio mediante `Depends`; la instancia real se configura en el `lifespan` de FastAPI.
- Repository Pattern: el acceso a PostgreSQL se ubica en `repositorios`, separado del dominio y rutas.
- Adapter / Infrastructure Layer: Redis, PostgreSQL, MQTT, metricas y logging estan encapsulados bajo `infraestructura`.
- Idempotency Key Pattern: `clave_idempotencia` garantiza que un retry no duplique la transferencia.
- Event-Driven / Producer Pattern: la API produce un evento transaccional para persistencia e IA.
- Transaction Script Pattern: Lua en Redis concentra una operacion atomica cercana al dato.
- Composition over Inheritance: el servicio recibe objetos colaboradores como `ScriptsRedis` y compone el comportamiento sin herencia.

## Manejo de concurrencia

La parte critica no se resuelve con locks en la aplicacion, sino con Redis Lua. Redis ejecuta cada script de forma atomica: mientras el script corre, no se intercalan otros comandos que modifiquen esas mismas claves. Esto evita condiciones de carrera entre validacion de saldo y actualizacion.

## Idempotencia

La clave `clave_idempotencia` se guarda en Redis con el resultado final. Si llega la misma solicitud otra vez, el script devuelve la respuesta anterior sin volver a debitar ni acreditar.

## Eventos posteriores

El evento se escribe en Redis Stream con:

- `transaccion_id`
- `trace_id`
- `cuenta_origen_id`
- `cuenta_destino_id`
- `monto`
- `moneda`
- `descripcion`
- `clave_idempotencia`
- `estado`
- `motivo`

## Observabilidad

La API expone:

- `/health`
- `/metrics`

Metricas relevantes:

- total de transacciones por estado y motivo
- duracion HTTP
- duracion de Redis/Lua
- errores de transaccion

Logs relevantes:

- `trace_id`
- `transaccion_id`
- `estado`
- `motivo`
- `clave_idempotencia`
- duracion en milisegundos

## Resultado de rendimiento

En pruebas locales se alcanzo aproximadamente 2000 TPS usando 4 workers de Uvicorn y los 4 cores asignados a Docker Desktop. Este valor queda documentado como evidencia del MVP local, no como limite teorico de arquitectura.

## Pendiente para completar

- Capturas de Grafana/k6.
- Explicacion de limites encontrados.
- Acciones para acercarse a 10 000 TPS en produccion: mas replicas, Redis Cluster, particionamiento de cuentas, broker administrado y tuning de red.
