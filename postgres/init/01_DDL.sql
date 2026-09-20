-- de ENUMs
CREATE TYPE tipo_cuenta_enum AS ENUM ('AHORROS', 'CORRIENTE');
CREATE TYPE estado_transaccion_enum AS ENUM ('COMPLETADA', 'RECHAZADA');
CREATE TYPE capacidad_financiera_enum AS ENUM ('FAVORABLE', 'MODERADA', 'REDUCIDA');
CREATE TYPE impacto_liquidez_enum AS ENUM ('BAJO', 'MODERADO', 'ALTO');

-- tabla de Clientes
CREATE TABLE clientes (
    id BIGINT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    ingresos_mensuales DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    gastos_mensuales DECIMAL(12, 2) NOT NULL DEFAULT 0.00, 
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- tabla de Cuentas
CREATE TABLE cuentas (
    id BIGINT PRIMARY KEY,
    cliente_id BIGINT NOT NULL,
    tipo_cuenta tipo_cuenta_enum NOT NULL DEFAULT 'CORRIENTE',
    saldo_centavos BIGINT NOT NULL DEFAULT 0,
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_cliente FOREIGN KEY (cliente_id) REFERENCES clientes(id),
    CONSTRAINT saldo_no_negativo CHECK (saldo_centavos >= 0)
);

-- 3. tabla de transacciones
CREATE TABLE transacciones (
    transaccion_id VARCHAR(64) PRIMARY KEY,
    trace_id VARCHAR(64) NOT NULL,
    clave_idempotencia VARCHAR(64) NOT NULL UNIQUE,
    cuenta_origen_id BIGINT NOT NULL,
    cuenta_destino_id BIGINT NOT NULL,
    monto_centavos BIGINT NOT NULL,
    moneda VARCHAR(6) NOT NULL,
    descripcion VARCHAR(255),
    estado estado_transaccion_enum NOT NULL,
    motivo VARCHAR(100) NOT NULL,
    creado_en TIMESTAMP WITH TIME ZONE
        NOT NULL DEFAULT CURRENT_TIMESTAMP
);

--Tabla para Almacenar la Respuesta del Servicio de IA
CREATE TABLE recomendaciones_ia (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cliente_id BIGINT NOT NULL,
    transaccion_id VARCHAR(64) NOT NULL,
    capacidad_financiera capacidad_financiera_enum NOT NULL,
    impacto_liquidez impacto_liquidez_enum NOT NULL,
    recomendacion TEXT NOT NULL,
    version_modelo VARCHAR(30) NOT NULL DEFAULT 'reglas-v1',
    generado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_cliente_ia FOREIGN KEY (cliente_id) REFERENCES clientes(id),
    CONSTRAINT fk_transaccion_ia FOREIGN KEY (transaccion_id) REFERENCES transacciones(transaccion_id)
);


-- indices para consultas

CREATE INDEX idx_cuentas_cliente
ON cuentas(cliente_id);
CREATE INDEX idx_transacciones_origen
ON transacciones(cuenta_origen_id);
CREATE INDEX idx_transacciones_destino
ON transacciones(cuenta_destino_id);
CREATE INDEX idx_transacciones_trace_id
ON transacciones(trace_id);
CREATE INDEX idx_transacciones_estado
ON transacciones(estado);
CREATE INDEX idx_transacciones_creado_en
ON transacciones(creado_en);
