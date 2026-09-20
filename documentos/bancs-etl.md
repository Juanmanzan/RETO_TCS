# Integracion con Bancs y ETL

## Objetivo

Explicar como SmartBancs se integra con un core legado Bancs sin saturarlo y como se transforma informacion transaccional para analitica o IA.

## Estrategia propuesta de integracion con Bancs

Completar con tu respuesta final. Base sugerida:

1. SmartBancs no consulta Bancs en cada transferencia del camino caliente.
2. Bancs publica o entrega lotes de saldos/cuentas en ventanas controladas.
3. SmartBancs mantiene una replica operativa de saldos en Redis para baja latencia.
4. Las transferencias se procesan en SmartBancs y se registran como eventos.
5. Un proceso de conciliacion envia lotes resumidos a Bancs.
6. Bancs confirma/aplica movimientos en horarios o canales controlados.
7. Las diferencias se detectan con conciliacion y alertas.

## Flujo teorico

```text
Bancs
  |
  | lote de cuentas/saldos/clientes
  v
ETL / normalizacion
  |
  | datos limpios
  v
PostgreSQL + Redis
  |
  | operaciones SmartBancs
  v
Eventos transaccionales
  |
  | lotes de conciliacion
  v
Bancs
```

## Justificacion

- Reduce consultas directas al core legado.
- Protege Bancs de picos de 10 000 TPS.
- Permite responder transferencias en menos de 2 segundos.
- Mantiene trazabilidad mediante `trace_id`, `transaccion_id` y `clave_idempotencia`.
- Facilita conciliacion y auditoria posterior.

## ETL practico

El directorio `ETL/` contiene:

- `bank_transactions_data_2-raw.csv`
- `ETL.py`
- `requirements.txt`

Completar aqui:

- Origen del archivo:
- Reglas de limpieza aplicadas:
- Manejo de nulos:
- Estandarizacion de formatos:
- Salida generada:
- Como se usaria para IA:

## Comandos

Instalar dependencias del ETL localmente:

```powershell
cd ETL
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python ETL.py
```

Volver a la raiz:

```powershell
cd ..
```

## Pendiente para completar

- Definir frecuencia de sincronizacion.
- Definir esquema de conciliacion.
- Definir manejo de inconsistencias.
- Definir estrategia ante caida temporal de Bancs.
