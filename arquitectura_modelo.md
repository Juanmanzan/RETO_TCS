## Arquitectura para el desarrollo del reto técnico base##

## Construcción de la API Rest para transacciones 

    FastAPI + PostgreSQL + Docker
    
    ¿Por qué FastAPI?: Permite procesar alta concurrencia de forma asíncrona nativa reduciendo el uso de servidores, e integra la lógica de IA en segundo plano sin bloquear el flujo principal de la transacción.

    ## Contrato de la petición 

    // json
    {
    "sourceAccountId": 1,    ## cuenta que envia
    "destinationAccountId": 2, ## cuenta de destino 
    "amount": 100.00, ## monto
    "currency": "USD", ## moneda 
    "description": "Pago de servicios", ## motivo de las trasaccion
    "idempotencyKey": "550e8400-e29b-41d4-a716-446655440000" ## key que permite identificar una misma transaccion aunque el usuario presione dos veces un boton 
    }

    ## Contrato de salida 
    {
    "transactionId": "TRX-000001", ## identificador de la transaccion
    "status": "COMPLETADA", ## estado de la transaccion pendiente / completada / rechazada / fallida 
    "sourceAccountId": 1, ## de donde se extrajo el dinero 
    "destinationAccountId": 2, ## a donde se envio el dinero 
    "amount": 100.00, ## el monto que transferido 
    "currency": "USD", ## la moneda 
    "createdAt": "2026-09-17T19:15:00Z" ## hora, fecha en la que se registro la transaccion 
    }

    ## observabilidad de la API 

    metricas a observar con VictoriaMetrics
    cantidad total de transacciones procesadas 
    transacciones exitosas y fallidas 
    tiempo de respuesta del endpoint de post/apis/transaccion
    errores en la base de datos deadlock detectados
    timeouts
    cantidad de conexiones activas pool hacia la base de datos 
    tiempo en que tarda postgres en registrar una transaccion 

    LOG que va a registrar por transaccion Structlog -> librería para generar logs estructurados en JSON nativo

   {
        "level": "INFO",
        "event": "transaction_completed",
        "transactionId": "TRX-1001",
        "correlationId": "8c32f4c1-7b8a-4d1d-a0a8-12ab34cd56ef", ## Sirve para rastrear una misma solicitud a través de varios componentes del sistema
        "sourceAccountId": 1,
        "destinationAccountId": 2,
        "amount": 100.00,
        "durationMs": 84,
        "timestamp": "2026-09-17T20:15:00Z"
    }

    {
        "level": "ERROR",
        "event": "transaction_failed",
        "transactionId": "TRX-1001",
        "correlationId": "8c32f4c1-7b8a-4d1d-a0a8-12ab34cd56ef",
        "sourceAccountId": 1,
        "destinationAccountId": 2,
        "amount": 100.00,
        "errorType": "DATABASE_TIMEOUT",
        "durationMs": 2050,
        "timestamp": "2026-09-17T20:15:02Z"
    }

## construccion de la API de IA 
   ## funcionalidades IA 
   Compara ingresos y gastos mensuales para estimar si el usuario tiene margen para ahorrar.
   Compara el monto de la transferencia con el saldo disponible para estimar si esa operación deja al usuario con poca liquidez.
   Con los resultados anteriores devuelve una sugerencia corta y útil.

   El servicio de inteligencia artificial funcionará como un analista financiero personal, encargado de revisar información financiera resumida del usuario y generar recomendaciones que le ayuden a organizar mejor su dinero, mantener liquidez y aprovechar oportunidades de ahorro.

   ## contrato
   {
        "id_usuario": 15,
        "ingresos_mensuales": 1200.00,
        "gastos_mensuales": 800.00,
        "saldo_actual": 900.00,
        "monto_transferencia": 300.00
    }

    ## Indicadores analizados

    El servicio calculará principalmente los siguientes indicadores:

    capacidad_disponible =
    ingresos_mensuales - gastos_mensuales

    porcentaje_gastos =
    gastos_mensuales / ingresos_mensuales

    impacto_transferencia =
    monto_transferencia / saldo_actual

    Estos indicadores permiten conocer de forma aproximada la situación financiera actual del usuario.

    ## Reglas de análisis

    ### Buena disponibilidad financiera

    Cuando los gastos representan hasta aproximadamente el 60 % de los ingresos, se considera que existe un margen favorable.

    Ejemplo:

    "¡Excelente! Mantienes un buen margen entre tus ingresos y gastos. Es un buen momento para pensar en tus objetivos futuros. Podrías considerar crear un plan de ahorro para aprovechar parte de tu disponibilidad mensual."

    Disponibilidad financiera moderada

    Cuando los gastos representan entre aproximadamente el 60 % y el 80 % de los ingresos.

    Ejemplo:

    "Mantienes un margen disponible para organizar tus próximos compromisos. Podrías establecer una meta de ahorro mensual que se ajuste a tu situación actual."

    Disponibilidad financiera reducida

    Cuando los gastos superan aproximadamente el 80 % de los ingresos.

    Ejemplo:

    "Este mes tienes un margen más ajustado. Te recomendamos priorizar tus próximos compromisos y mantener una reserva disponible antes de definir nuevas metas de ahorro."

    ## Impacto de la transferencia

    Impacto bajo

    Cuando la transferencia representa hasta aproximadamente el 30 % del saldo:

    "La operación mantiene una buena parte de tu saldo disponible. Puedes continuar organizando tus próximas metas financieras con tranquilidad."

    Impacto moderado

    Cuando representa entre aproximadamente el 30 % y el 60 % del saldo:

    "Después de esta operación todavía mantendrás disponibilidad, aunque sería conveniente considerar tus próximos pagos antes de realizar nuevos movimientos importantes."

    Impacto alto

    Cuando supera aproximadamente el 60 % del saldo:

    "Esta operación representa una parte importante de tu saldo actual. Te recomendamos mantener una reserva para tus próximos compromisos financieros."

    Recomendaciones combinadas

    El servicio podrá combinar la capacidad financiera y el impacto de la transferencia para generar una recomendación más natural.

    Ejemplo de situación favorable:

    "¡Vas por buen camino! Mantienes un margen financiero favorable incluso después de esta operación. ¿Has pensado en tus objetivos futuros? Podrías destinar parte de tu disponibilidad a un plan de ahorro."

    Ejemplo de menor disponibilidad:

    "Después de esta operación tu disponibilidad podría quedar más ajustada. Te recomendamos mantener una reserva para tus próximos compromisos antes de establecer nuevas metas financieras."

    contrato de respuesta 

    { 
        "id_usuario": 15, 
        "capacidad_financiera": "FAVORABLE", 
        "impacto_liquidez": "BAJO", 
        "recomendacion": "¡Vas por buen camino! Mantienes un margen financiero favorable. Podrías considerar establecer una meta de ahorro para aprovechar parte de tu disponibilidad.", 
        "version_modelo": "reglas-v1" 
    }


arquitectura transaccion 




api-transacciones/
│
├── Dockerfile
├── .dockerignore
├── requirements.txt
│
├── app/
│   │
│   ├── main.py
│   ├── registro_rutas.py
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py
│   │
│   ├── rutas/
│   │   ├── __init__.py
│   │   └── transacciones.py
│   │
│   ├── esquemas/
│   │   ├── __init__.py
│   │   └── transacciones.py
│   │
│   ├── servicios/
│   │   ├── __init__.py
│   │   └── transacciones.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── excepciones.py
│   │   │
│   │   └── transacciones/
│   │       ├── __init__.py
│   │       ├── ids.py
│   │       ├── montos.py
│   │       ├── validaciones.py
│   │       └── resultados.py
│   │
│   ├── infraestructura/
│   │   ├── __init__.py
│   │   │
│   │   ├── redis/
│   │   │   ├── __init__.py
│   │   │   ├── conexion.py
│   │   │   ├── scripts.py
│   │   │   └── transferencia.lua
│   │   │
│   │   ├── postgres/
│   │   │   ├── __init__.py
│   │   │   ├── conexion.py
│   │   │   └── pool.py
│   │   │
│   │   ├── mensajeria/
│   │   │   ├── __init__.py
│   │   │   └── rabbitmq.py
│   │   │
│   │   └── observabilidad/
│   │       ├── __init__.py
│   │       ├── metricas.py
│   │       └── logging.py
│   │
│   ├── modelos/
│   │   ├── __init__.py
│   │   └── transaccion.py
│   │
│   ├── repositorios/
│   │   ├── __init__.py
│   │   └── transacciones.py
│   │
│   └── workers/
│       ├── __init__.py
│       ├── publicador_eventos.py
│       └── persistencia.py
│
└── tests/
    ├── unitarias/
    ├── integracion/
    └── carga/