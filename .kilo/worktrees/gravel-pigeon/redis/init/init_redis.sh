#!/bin/sh
set -e

export REDISCLI_AUTH="$REDIS_PASSWORD"

# registra los ids de las cuentas de postgret con un saldo correspondiente en centavos 
redis-cli \
  --user "$REDIS_USER" \
  -h "$REDIS_HOST" \
  -p "$REDIS_PORT" \
  -n "$REDIS_DB" \
  SETNX 1001 500000

redis-cli \
  --user "$REDIS_USER" \
  -h "$REDIS_HOST" \
  -p "$REDIS_PORT" \
  -n "$REDIS_DB" \
  SETNX 1002 1250000

redis-cli \
  --user "$REDIS_USER" \
  -h "$REDIS_HOST" \
  -p "$REDIS_PORT" \
  -n "$REDIS_DB" \
  SETNX 1003 85000

redis-cli \
  --user "$REDIS_USER" \
  -h "$REDIS_HOST" \
  -p "$REDIS_PORT" \
  -n "$REDIS_DB" \
  SETNX 1004 2200000

redis-cli \
  --user "$REDIS_USER" \
  -h "$REDIS_HOST" \
  -p "$REDIS_PORT" \
  -n "$REDIS_DB" \
  SETNX 1005 32000

echo "saldos iniciales cargados correctamente"