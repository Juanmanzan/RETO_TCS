# ETL

## Objetivo

Explicar como se ejecuta el script (mock) de ETL que transforma el dataset crudo de transacciones bancarias en un archivo limpio y estandarizado, listo para cargarse en el esquema SQL del proyecto.

## ETL practico

El directorio `ETL/` contiene:

- `bank_transactions_data_2-raw.csv`
- `ETL.py`
- `requirements.txt`

Instalar dependencias del ETL localmente:

```powershell
cd ETL
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

```

Ejecutar script:

```powershell
python ETL.py
```

## Datos generales del proceso

- **Origen del archivo:** extraido de [Bank Transaction Dataset for Fraud Detection](https://www.kaggle.com/datasets/valakhorasani/bank-transaction-dataset-for-fraud-detection).
- **Salida generada:** un CSV limpio con los registros que pasaron todas las validaciones, 
un CSV separado con los registros descartados: duplicados, nulos, fechas invalidas, estados desconocidos, cuentas destino invalidas, montos o monedas invalidas y un grafico resumen con las metricas de correccion del proceso.
- **Como se usaria para IA:** el CSV limpio sirve como insumo para poblar y enriquecer las tablas de cuentas y clientes que consulta `worker-ia`, y como dataset de referencia para calibrar los umbrales de `capacidad_financiera` e `impacto_liquidez` del modelo de reglas.

## Estrategia de limpieza

Pasos seguidos por `ETL.py` para transformar el dataset crudo:

1. **Seleccion de columnas:** se listan las columnas actuales del dataset y se conserva unicamente las columnas necesarias segun el esquema SQL del proyecto.
2. **Eliminacion de duplicados:** se identifican los registros duplicados por `TransactionID`, se cuenta cuantos existen y se conserva solo el primero, descartando el resto.
3. **Manejo de nulos:** se convierten las cadenas vacias o con solo espacios en valores nulos. Se descartan las transacciones sin `TransactionAmount` o sin fecha, por considerarse invalidas. Si falta el tipo de moneda, se completa con `USD` por defecto. Se valida que los tres identificadores de la transaccion no esten vacios; se cuentan y se separan en una lista aparte los registros con algun id nulo, y se continua solo con los registros que si tienen todos sus ids.
4. **Estandarizacion de fechas:** se intenta convertir los distintos formatos de fecha presentes en el dataset (ISO con y sin `T`, `DD/MM/AAAA`, `MM-DD-AAAA`, `DD-Mon-AAAA` con AM/PM, `AAAA/MM/DD`) a un unico formato. Las fechas que no logran convertirse se separan como invalidas, y las validas reciben zona horaria y se normalizan al estandar ISO 8601.
5. **Estandarizacion del estado de la transaccion:** se limpian espacios y se pasa el texto a minusculas; los valores se mapean contra un enum de estados conocido. Los estados que no pertenecen a ese enum se guardan aparte, junto con su texto original, para poder investigarlos, y se continua solo con los estados validos.
6. **Limpieza de campos de texto:** `Currency` se estandariza en mayusculas, el motivo conserva un formato legible, y se recortan espacios en los identificadores.
7. **Validacion de integridad de `AccountDestinoID`:** se genera el conjunto de cuentas validas conocidas (`AC00001` a `AC00500`). Se identifican las transacciones cuya cuenta destino no pertenece a ese conjunto, se contrasta con los casos donde el propio dataset ya marcaba el error en el campo `Motivo`, y se retiran del conjunto limpio las cuentas destino inconsistentes.
8. **Tipos y formato final:** se convierte el monto a numerico, marcando y separando los valores que no pueden convertirse. Si el esquema almacena el monto en `BIGINT` (centavos), se multiplica por 100 y se redondea. Se valida que `Currency` tenga exactamente 3 letras, separando las monedas invalidas. Finalmente se renombran las columnas de acuerdo al esquema SQL.
9. **Exportacion del CSV limpio:** se genera el archivo final con los registros que superaron todas las validaciones anteriores.
10. **Exportacion de registros incorrectos:** los registros descartados en cada paso se exportan aparte para su revision.
11. **Generacion de grafico de metricas:** se genera un resumen visual con las estadisticas de las correcciones realizadas durante el proceso.
