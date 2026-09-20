from prometheus_client import Counter, Histogram


RECOMENDACIONES_SOLICITADAS_TOTAL = Counter(
    "smartbancs_ia_recomendaciones_solicitadas_total",
    "Total de recomendaciones solicitadas por endpoint o worker",
    ["origen"],
)


RECOMENDACIONES_PROCESADAS_TOTAL = Counter(
    "smartbancs_ia_recomendaciones_procesadas_total",
    "Total de recomendaciones procesadas por la ia",
    ["origen", "capacidad_financiera", "impacto_liquidez"],
)


RECOMENDACIONES_PERSISTIDAS_TOTAL = Counter(
    "smartbancs_ia_recomendaciones_persistidas_total",
    "Total de recomendaciones guardadas en PostgreSQL",
)


ERRORES_IA_TOTAL = Counter(
    "smartbancs_ia_errores_total",
    "Total de errores del servicio de ia",
    ["tipo"],
)


EVENTOS_IA_RECIBIDOS_TOTAL = Counter(
    "smartbancs_ia_eventos_recibidos_total",
    "Total de eventos recibidos desde MQTT para ia",
)


EVENTOS_IA_DESCARTADOS_TOTAL = Counter(
    "smartbancs_ia_eventos_descartados_total",
    "Total de eventos descartados por la ia",
    ["motivo"],
)


DURACION_RECOMENDACION = Histogram(
    "smartbancs_ia_recomendacion_duracion_seconds",
    "Tiempo usado para generar una recomendacion",
    buckets=(
        0.001,
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1,
        2,
        5,
    ),
)
