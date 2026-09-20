import pandas as pd
import matplotlib.pyplot as plt


## ruta del archivo CSV para su procesamiento

Ruta_csv = "bank_transactions_data_2-raw.csv"
ZONA_HORARIA_ORIGEN = "America/Guayaquil"

columnas_transacciones = [
    "TransactionID",
    "AccountID",
    "AccountDestinoID",
    "TransactionAmount",
    "Currency",
    "TransactionDate",
    "TransactionStatus",
    "Motivo",
]

estadisticas = {} ## diccionario vacio para registrar los cambios realizados


## leer el archivo csv
## obtenemos un data frame resultante datos
datos = pd.read_csv(Ruta_csv)

print("inicio del proceso ETL")

## 1 seleccion de columnas

print("\nobtencion de las columnas necesarias para la tabla de transacciones")

## se imprime el nombre de las columnas actuales del data frame
print("\ncolumnas actuales")
print(datos.columns.to_list())

## creamos otro data frame seleccionando solamente las columnas que nos interesa
## de acuerdo a nuestro esquema SQL
datos_sql = datos[columnas_transacciones].copy()

print("\ncolumnas seleccionadas")
print(datos_sql.columns.tolist())

estadisticas["columnas_descartadas"] = len(datos.columns) - len(datos_sql.columns)


## 2 eliminar duplicados

print("\nverificacion de datos duplicados")

## contador para contrastar posteriormente cuantos registros duplicados existian
registros_anteriores = len(datos_sql)

## identifica los datos duplicados del data frame que coincidan con el mismo TransactionID
## se queda con el primer resultado, todos los demas duplicados se descartan
duplicados = datos_sql.duplicated(subset=["TransactionID"], keep="first").sum()

estadisticas["duplicados_eliminados"] = int(duplicados)

print(f"\ncantidad de datos: {registros_anteriores}")
print(f"cantidad de datos duplicados: {duplicados}")

## eliminar datos duplicados
datos_sql = datos_sql.drop_duplicates(subset=["TransactionID"], keep="first")
registros_despues = len(datos_sql)
print(f"registros antes de verificar duplicacion: {registros_anteriores}")
print(f"registros despues de verificar duplicacion: {registros_despues}")


## 3 manejo de nulos

print("\nManejo de nulos")
## convertimos cadenas vacias o espacios en valores nulos
datos_sql = datos_sql.replace(r"^\s*$", None, regex=True)

print("\nMontos faltantes")

## elimina los registros que tengan null en TransactionAmount
## una transaccion que no tenga un monto no es valida
nulos_monto = datos_sql["TransactionAmount"].isna().sum()
datos_sql = datos_sql.dropna(subset=["TransactionAmount"])
estadisticas["filas_eliminadas_monto_nulo"] = int(nulos_monto)


print("\nSin fechas")

## una transaccion sin fecha tampoco es valida
nulos_fecha = datos_sql["TransactionDate"].isna().sum()
datos_sql = datos_sql.dropna(subset=["TransactionDate"])
estadisticas["filas_eliminadas_fecha_nula"] = int(nulos_fecha)


## si no existe el tipo de moneda la completamos con USD
nulos_moneda = datos_sql["Currency"].isna().sum()
datos_sql["Currency"] = datos_sql["Currency"].fillna("USD")
estadisticas["registros_completados_moneda"] = int(nulos_moneda)


## transacciones con ids null
nulos_destino = datos_sql["AccountDestinoID"].isna().sum()
nulos_origen = datos_sql["AccountID"].isna().sum()
nulos_transaccion = datos_sql["TransactionID"].isna().sum()

## almacenamos cuantos ids nulos encontramos
estadisticas["destinos_desconocidos_nulos"] = int(nulos_destino)
estadisticas["destinos_origen_nulos"] = int(nulos_origen)
estadisticas["TransactionID_nulos"] = int(nulos_transaccion)


print("\ndeteccion de registros que no tengan un id")

## verifica si alguno de los tres identificadores esta vacio
## si alguno es null marca la fila como True
buscar_registros_sin_id = datos_sql[
    ["TransactionID", "AccountID", "AccountDestinoID"]
].isna().any(axis=1)

## guardamos las transacciones sin id en una lista de diccionarios
transacciones_sin_id = datos_sql[
    buscar_registros_sin_id
].to_dict(orient="records")

estadisticas["transacciones_separadas_sin_id"] = len(transacciones_sin_id)

## continuamos solamente con los registros que SI tienen todos sus ids
datos_sql = datos_sql[~buscar_registros_sin_id].copy()

print(f"transacciones separadas por ids incompletos: {len(transacciones_sin_id)}")
print(f"transacciones que continuan: {len(datos_sql)}")


## 4 estandarizar formato de fechas

print("\nestandarizar formato de fechas")


def convertir_fecha(fecha):
    formatos = [
        "%Y-%m-%dT%H:%M:%S",   ## 2026-08-15T14:30:00
        "%Y-%m-%d %H:%M:%S",   ## 2026-08-15 14:30:00
        "%d/%m/%Y %H:%M",      ## 15/08/2026 14:30
        "%m-%d-%Y",             ## 08-15-2026
        "%d-%b-%Y %I:%M %p",   ## 15-Aug-2026 02:30 PM
        "%Y/%m/%d",             ## 2026/08/15
    ]

    for formato in formatos:
        try:
            return pd.to_datetime(fecha, format=formato)
        except (ValueError, TypeError):
            continue

    return pd.NaT ## no es un dato valido de tipo tiempo


## intentar convertir todas las fechas
datos_sql["TransactionDate"] = datos_sql["TransactionDate"].apply(convertir_fecha)
## detectar fechas que no pudieron convertirse
buscar_fecha_invalida = datos_sql["TransactionDate"].isna()
fechas_invalidas = buscar_fecha_invalida.sum()
estadisticas["fechas_formato_invalido"] = int(fechas_invalidas)
## separar registros con fecha invalida
transacciones_fecha_invalida = datos_sql[
    buscar_fecha_invalida
].to_dict(orient="records")

## continuar solamente con las fechas validas
datos_sql = datos_sql[~buscar_fecha_invalida].copy()
## agregar zona horaria
datos_sql["TransactionDate"] = datos_sql["TransactionDate"].dt.tz_localize(
    ZONA_HORARIA_ORIGEN
)

## convertir al estandar ISO 8601
datos_sql["TransactionDate"] = datos_sql[
    "TransactionDate"
].apply(lambda fecha: fecha.isoformat())
print(f"fechas invalidas encontradas: {fechas_invalidas}")
print(f"transacciones que continuan: {len(datos_sql)}")


## 5 estandarizar estado de la transaccion

print("\nestandarizar TransactionStatus")
## limpiamos espacios y convertimos los estados a minusculas
datos_sql["TransactionStatus"] = (
    datos_sql["TransactionStatus"]
    .astype(str)
    .str.strip()
    .str.lower()
)

## diccionario que representa nuestro enum de estados
mapa_estados = {
    "completed": "COMPLETADA",
    "success": "COMPLETADA",
    "failed": "RECHAZADA",
    "declined": "RECHAZADA",
}

## guardamos los estados originales para saber cuales no pudieron mapearse
estado_original = datos_sql["TransactionStatus"].copy()
## reemplazamos los estados por los valores de nuestro enum
datos_sql["TransactionStatus"] = datos_sql["TransactionStatus"].map(mapa_estados)
## detectar estados que no pertenecen al enum conocido
buscar_estado_invalido = datos_sql["TransactionStatus"].isna()
estados_invalidos = buscar_estado_invalido.sum()
estadisticas["estados_invalidos"] = int(estados_invalidos)
## guardamos estas transacciones para poder investigarlas
transacciones_estado_invalido = datos_sql[
    buscar_estado_invalido
].copy()
## agregamos nuevamente el texto original del estado para saber cual produjo el error
transacciones_estado_invalido["EstadoOriginal"] = estado_original[
    buscar_estado_invalido
]
transacciones_estado_invalido = transacciones_estado_invalido.to_dict(
    orient="records"
)
## continuamos solamente con los estados validos
datos_sql = datos_sql[~buscar_estado_invalido].copy()
print(f"estados invalidos encontrados: {estados_invalidos}")


## 6 limpiar campos de texto
print("\nlimpieza de campos de texto")
## Currency se maneja en mayusculas
datos_sql["Currency"] = datos_sql["Currency"].astype(str).str.strip().str.upper()
## Motivo puede conservar un formato legible
datos_sql["Motivo"] = datos_sql["Motivo"].fillna("").astype(str).str.strip()
## limpiamos tambien espacios en los identificadores
datos_sql["TransactionID"] = datos_sql["TransactionID"].astype(str).str.strip()
datos_sql["AccountID"] = datos_sql["AccountID"].astype(str).str.strip().str.upper()
datos_sql["AccountDestinoID"] = datos_sql["AccountDestinoID"].astype(str).str.strip().str.upper()


## 7 validar integridad de AccountDestinoID
print("\nvalidacion de cuentas destino")
## generamos las cuentas que existen segun el rango conocido
## AC00001 hasta AC00500
cuentas_validas = {
    f"AC{numero:05d}"
    for numero in range(1, 501)
}

## verificar si AccountDestinoID pertenece al conjunto de cuentas conocidas
buscar_destino_invalido = ~datos_sql["AccountDestinoID"].isin(cuentas_validas)
destinos_invalidos = buscar_destino_invalido.sum()
estadisticas["cuentas_destino_invalidas"] = int(destinos_invalidos)

## guardamos las transacciones cuyo destino no existe
transacciones_destino_invalido = datos_sql[
    buscar_destino_invalido
].to_dict(orient="records")

## verificar si el dataset ya habia identificado el mismo problema mediante Motivo
motivo_destino_no_existe = (
    datos_sql["Motivo"]
    .str.strip()
    .str.lower()
    .eq("cuenta destino no existe")
)

## registros donde nuestro control detecto destino invalido
## y el dato crudo tambien lo identificaba
coincidencias_destino = (
    buscar_destino_invalido & motivo_destino_no_existe
).sum()
estadisticas["coincidencias_destino_motivo"] = int(coincidencias_destino)
print(f"cuentas destino invalidas: {destinos_invalidos}")
print(f"coincidencias con Motivo: {coincidencias_destino}")

## retiramos las cuentas destino inconsistentes del conjunto limpio
datos_sql = datos_sql[~buscar_destino_invalido].copy()


## 8 tipos y formato final


print("\nconversion de tipos finales")

## convertir monto a numero
## cualquier valor que no pueda convertirse se transforma en NaN
datos_sql["TransactionAmount"] = pd.to_numeric(
    datos_sql["TransactionAmount"],
    errors="coerce"
)

## detectar montos con formato incorrecto
buscar_monto_invalido = datos_sql["TransactionAmount"].isna()

montos_invalidos = buscar_monto_invalido.sum()

estadisticas["montos_formato_invalido"] = int(montos_invalidos)

## guardar registros cuyo monto no pudo convertirse
transacciones_monto_invalido = datos_sql[
    buscar_monto_invalido
].to_dict(orient="records")

## continuar solamente con montos validos
datos_sql = datos_sql[~buscar_monto_invalido].copy()


## si el esquema almacena el monto en centavos usando BIGINT
## multiplicamos por 100 y redondeamos
datos_sql["TransactionAmount"] = (
    datos_sql["TransactionAmount"] * 100
).round().astype("int64")


## Currency debe contener exactamente 3 letras
buscar_moneda_invalida = ~datos_sql["Currency"].str.fullmatch(r"[A-Z]{3}")

monedas_invalidas = buscar_moneda_invalida.sum()

estadisticas["monedas_formato_invalido"] = int(monedas_invalidas)

## separar registros con moneda invalida
transacciones_moneda_invalida = datos_sql[
    buscar_moneda_invalida
].to_dict(orient="records")

## continuar solamente con monedas validas
datos_sql = datos_sql[~buscar_moneda_invalida].copy()


## renombrar las columnas de acuerdo al esquema SQL
datos_sql = datos_sql.rename(
    columns={
        "TransactionID": "transaccion_id",
        "AccountID": "cuenta_origen_id",
        "AccountDestinoID": "cuenta_destino_id",
        "TransactionAmount": "monto_centavos",
        "Currency": "moneda",
        "TransactionDate": "creado_en",
        "TransactionStatus": "estado",
        "Motivo": "motivo",
    }
)

## 9 exportar csv limpio
print("\nexportando datos limpios")
datos_sql.to_csv(
    "transacciones_limpias.csv",
    index=False,
    encoding="utf-8"
)

estadisticas["registros_finales_limpios"] = len(datos_sql)

## 10 exportar registros incorrectos

print("\ngenerando reporte de registros incorrectos")

with open("registros_invalidos.txt", "w", encoding="utf-8") as archivo:

    archivo.write("reporte de registros invalidos del proceso etlL\n")
    archivo.write("=" * 60 + "\n\n")

    archivo.write("transacciones con ids nulos\n")
    archivo.write("-" * 60 + "\n")

    for transaccion in transacciones_sin_id:
        archivo.write(f"{transaccion}\n")

    archivo.write("\n\ntransacciones con fecha invalida\n")
    archivo.write("-" * 60 + "\n")

    for transaccion in transacciones_fecha_invalida:
        archivo.write(f"{transaccion}\n")

    archivo.write("\n\ntransacciones con estado invalido\n")
    archivo.write("-" * 60 + "\n")

    for transaccion in transacciones_estado_invalido:
        archivo.write(f"{transaccion}\n")

    archivo.write("\n\ntransacciones con cuenta destino invalida\n")
    archivo.write("-" * 60 + "\n")

    for transaccion in transacciones_destino_invalido:
        archivo.write(f"{transaccion}\n")

    archivo.write("\n\ntransacciones con monto invalido\n")
    archivo.write("-" * 60 + "\n")

    for transaccion in transacciones_monto_invalido:
        archivo.write(f"{transaccion}\n")

    archivo.write("\n\ntransacciones con moneda invalida\n")
    archivo.write("-" * 60 + "\n")

    for transaccion in transacciones_moneda_invalida:
        archivo.write(f"{transaccion}\n")


## 11 generar grafico de metricas

print("\ngenerando grafico de metricas")

## seleccionamos solamente las estadisticas relacionadas con correcciones
metricas_grafico = {
    "Duplicados": estadisticas.get("duplicados_eliminados", 0),
    "Monto nulo": estadisticas.get("filas_eliminadas_monto_nulo", 0),
    "Fecha nula": estadisticas.get("filas_eliminadas_fecha_nula", 0),
    "Moneda completada": estadisticas.get("registros_completados_moneda", 0),
    "IDs incompletos": estadisticas.get("transacciones_separadas_sin_id", 0),
    "Fechas invalidas": estadisticas.get("fechas_formato_invalido", 0),
    "Estados invalidos": estadisticas.get("estados_invalidos", 0),
    "Destino invalido": estadisticas.get("cuentas_destino_invalidas", 0),
    "Monto invalido": estadisticas.get("montos_formato_invalido", 0),
    "Moneda invalida": estadisticas.get("monedas_formato_invalido", 0),
}
plt.figure(figsize=(12, 6))
plt.bar(
    metricas_grafico.keys(),
    metricas_grafico.values()
)
plt.title("Correcciones realizadas durante el proceso ETL")
plt.xlabel("Tipo de correccion")
plt.ylabel("Cantidad de registros")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.savefig("metricas_etl.png",dpi=300)
plt.close()


## resumen final

print("proceso finalizado")

for nombre, valor in estadisticas.items():
    print(f"{nombre}: {valor}")

print("\narchivos generados:")
print("transacciones_limpias.csv")
print("registros_invalidos.txt")
print("metricas_etl.png")
