import atexit
import json
import logging
from datetime import datetime, timezone
from logging.handlers import QueueHandler, QueueListener
from queue import SimpleQueue
from typing import Any


## cola utilizada para desacoplar la generación del log
## de su escritura hacia stdout
_cola_logs: SimpleQueue = SimpleQueue()


## referencia global al listener para evitar crear
## múltiples listeners dentro del mismo proceso
_listener_logs: QueueListener | None = None


class FormateadorJson(logging.Formatter):

    def format(self, record: logging.LogRecord) -> str:

        log = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "nivel": record.levelname,
            "logger": record.name,
            "mensaje": record.getMessage(),
        }

        campos = (
            "componente",
            "evento",
            "trace_id",
            "transaccion_id",
            "estado",
            "motivo",
            "evento_id",
            "clave_idempotencia",
            "duracion_ms",
        )

        for campo in campos:

            valor = getattr(
                record,
                campo,
                None,
            )

            if valor is not None:
                log[campo] = valor

        if record.exc_info:

            log["error"] = self.formatException(
                record.exc_info
            )

        return json.dumps(
            log,
            ensure_ascii=False,
        )


def detener_logging() -> None:

    global _listener_logs

    if _listener_logs is not None:

        _listener_logs.stop()

        _listener_logs = None


def configurar_logging() -> None:

    global _listener_logs

    ## evita crear múltiples QueueListener dentro
    ## del mismo proceso
    if _listener_logs is not None:
        return

    ## handler real encargado de escribir finalmente
    ## el log hacia stdout
    manejador_salida = logging.StreamHandler()

    manejador_salida.setFormatter(
        FormateadorJson()
    )

    ## listener que consume los LogRecord desde la cola
    ## en un hilo separado
    _listener_logs = QueueListener(
        _cola_logs,
        manejador_salida,
        respect_handler_level=True,
    )

    _listener_logs.start()

    ## handler utilizado por los loggers de la aplicación.
    ## únicamente coloca el LogRecord dentro de la cola
    ## sin realizar directamente la escritura a stdout.
    manejador_cola = QueueHandler(
        _cola_logs
    )

    logger_raiz = logging.getLogger()

    logger_raiz.handlers.clear()

    logger_raiz.addHandler(
        manejador_cola
    )

    logger_raiz.setLevel(
        logging.INFO
    )

    ## garantiza que el listener se detenga correctamente
    ## cuando finaliza el proceso
    atexit.register(
        detener_logging
    )


def registrar_evento(
    logger: logging.Logger,
    mensaje: str,
    *,
    componente: str,
    evento: str,
    trace_id: str | None = None,
    transaccion_id: str | None = None,
    estado: str | None = None,
    motivo: str | None = None,
    evento_id: str | None = None,
    clave_idempotencia: str | None = None,
    duracion_ms: float | None = None,
    nivel: int = logging.INFO,
) -> None:

    logger.log(
        nivel,
        mensaje,
        extra={
            "componente": componente,
            "evento": evento,
            "trace_id": trace_id,
            "transaccion_id": transaccion_id,
            "estado": estado,
            "motivo": motivo,
            "evento_id": evento_id,
            "clave_idempotencia": clave_idempotencia,
            "duracion_ms": duracion_ms,
        },
    )
