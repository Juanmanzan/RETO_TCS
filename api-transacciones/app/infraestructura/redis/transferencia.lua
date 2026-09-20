-- obtiene las claves utilizadas durante la transferencia
local cuenta_origen = KEYS[1] -- identificador de la cuenta de origen en redis 
local cuenta_destino = KEYS[2] -- identificador de la cuenta de destino en redis
local clave_idempotencia = KEYS[3] -- identificador de idepotencia para verificar si no se registro la misma transaccion anteriormente 
local stream_transacciones = KEYS[4] -- identificador 

-- obtiene los datos enviados desde fastapi para la transaccion 
local transaccion_id = ARGV[1]
local trace_id = ARGV[2]
local monto = tonumber(ARGV[3])
local moneda = ARGV[4]
local descripcion = ARGV[5]
local clave_idempotencia = ARGV[6]


-- verifica si la clave de idempotencia ya fue procesada
local resultado_anterior = redis.call(
    "GET",
    clave_idempotencia
)


--- si no se devuelve nill existe ya una transaccion con esa idempotency_key
-- extraemos los valores de dicho registro de redis y devolvemos a FastApi
if resultado_anterior then

    -- separa los datos almacenados anteriormente

    -- "tx_9876|APROBADA|SALDO_SUFICIENTE" ejemplo de trasaccion 

    -- obtiene el indice del primer separador |
    local separador_1 = string.find(
        resultado_anterior,
        "|"
    )

    -- obtiene la posicion del segundo separador 
    local separador_2 = string.find(
        resultado_anterior,
        "|",
        separador_1 + 1
    )

    -- extraye el valor de la clave de idepotencia 
    local transaccion_anterior = string.sub(
        resultado_anterior,
        1,
        separador_1 - 1
    )

    -- extrae el estado de la operacion aprobada, rechazada
    local estado_anterior = string.sub(
        resultado_anterior,
        separador_1 + 1,
        separador_2 - 1
    )

    -- extrae el motivo que se concreto de la anterior transaccion 
    local motivo_anterior = string.sub(
        resultado_anterior,
        separador_2 + 1
    )

    return {
        "IDEMPOTENTE",
        transaccion_anterior,
        estado_anterior,
        motivo_anterior
    }

end


-- verifica que el monto enviado sea valido
if not monto or monto <= 0 then

    local estado = "RECHAZADA"
    local motivo = "MONTO_INVALIDO"

    -- registra el resultado en redis evitar procesar nuevamente la misma solicitud
    redis.call(
        "SET",
        clave_idempotencia,
        transaccion_id .. "|" .. estado .. "|" .. motivo
    )

    -- registra el intento rechazado en el stream
    redis.call(
        "XADD",
        stream_transacciones,
        "*",
        "transaccion_id", transaccion_id,
        "trace_id", trace_id,
        "cuenta_origen_id", cuenta_origen,
        "cuenta_destino_id", cuenta_destino,
        "monto", tostring(monto or 0),
        "moneda", moneda,
        "descripcion", descripcion,
        "clave_idempotencia", clave_idempotencia,
        "estado", estado,
        "motivo", motivo
    )

    return {
        "RECHAZADA",
        transaccion_id,
        estado,
        motivo
    }
    
end


-- verifica que la cuenta de origen exista en redis
if redis.call("EXISTS", cuenta_origen) == 0 then

    local estado = "RECHAZADA"
    local motivo = "CUENTA_ORIGEN_NO_EXISTE"

    redis.call(
        "SET",
        clave_idempotencia,
        transaccion_id .. "|" .. estado .. "|" .. motivo
    )

    redis.call(
        "XADD",
        stream_transacciones,
        "*",
        "transaccion_id", transaccion_id,
        "trace_id", trace_id,
        "cuenta_origen_id", cuenta_origen,
        "cuenta_destino_id", cuenta_destino,
        "monto", tostring(monto),
        "moneda", moneda,
        "descripcion", descripcion,
        "clave_idempotencia", clave_idempotencia,
        "estado", estado,
        "motivo", motivo
    )

    return {
        "RECHAZADA",
        transaccion_id,
        estado,
        motivo
    }
end


-- verifica que la cuenta de destino exista en redis
if redis.call("EXISTS", cuenta_destino) == 0 then

    local estado = "RECHAZADA"
    local motivo = "CUENTA_DESTINO_NO_EXISTE"

    redis.call(
        "SET",
        clave_idempotencia,
        transaccion_id .. "|" .. estado .. "|" .. motivo
    )

    redis.call(
        "XADD",
        stream_transacciones,
        "*",
        "transaccion_id", transaccion_id,
        "trace_id", trace_id,
        "cuenta_origen_id", cuenta_origen,
        "cuenta_destino_id", cuenta_destino,
        "monto", tostring(monto),
        "moneda", moneda,
        "descripcion", descripcion,
        "clave_idempotencia", clave_idempotencia,
        "estado", estado,
        "motivo", motivo
    )

    return {
        "RECHAZADA",
        transaccion_id,
        estado,
        motivo
    }
end


-- obtiene el saldo actual de la cuenta de origen
local saldo_origen = tonumber(
    redis.call(
        "GET",
        cuenta_origen
    )
)


-- verifica que la cuenta tenga fondos suficientes
if saldo_origen < monto then

    local estado = "RECHAZADA"
    local motivo = "FONDOS_INSUFICIENTES"

    redis.call(
        "SET",
        clave_idempotencia,
        transaccion_id .. "|" .. estado .. "|" .. motivo
    )

    redis.call(
        "XADD",
        stream_transacciones,
        "*",
        "transaccion_id", transaccion_id,
        "trace_id", trace_id,
        "cuenta_origen_id", cuenta_origen,
        "cuenta_destino_id", cuenta_destino,
        "monto", tostring(monto),
        "moneda", moneda,
        "descripcion", descripcion,
        "clave_idempotencia", clave_idempotencia,
        "estado", estado,
        "motivo", motivo
    )

    return {
        "RECHAZADA",
        transaccion_id,
        estado,
        motivo
    }
end


-- descuenta el monto de la cuenta de origen
redis.call(
    "DECRBY",
    cuenta_origen,
    monto
)


-- acredita el monto en la cuenta de destino
redis.call(
    "INCRBY",
    cuenta_destino,
    monto
)


local estado = "COMPLETADA"
local motivo = "OK"


-- registra el resultado de la operacion para controlar la idempotencia
redis.call(
    "SET",
    clave_idempotencia,
    transaccion_id .. "|" .. estado .. "|" .. motivo
)


-- registra la transaccion completada en el stream
redis.call(
    "XADD",
    stream_transacciones,
    "*",
    "transaccion_id", transaccion_id,
    "trace_id", trace_id,
    "cuenta_origen_id", cuenta_origen,
    "cuenta_destino_id", cuenta_destino,
    "monto", tostring(monto),
    "moneda", moneda,
    "descripcion", descripcion,
    "clave_idempotencia", clave_idempotencia,
    "estado", estado,
    "motivo", motivo
)


-- devuelve el resultado hacia fastapi
return {
    "COMPLETADA",
    transaccion_id,
    estado,
    motivo
}