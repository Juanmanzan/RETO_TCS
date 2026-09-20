import atexit
import json
import logging
from datetime import datetime, timezone
from logging.handlers import QueueHandler, QueueListener
from queue import SimpleQueue


## cola usada para no escribir directo en stdout
_cola_logs: SimpleQueue = SimpleQueue()


## listener global para evitar duplicarlo dentro del proceso
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
            "cliente_id",
            "cuenta_origen_id",
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

    if _listener_logs is not None:
        return

    manejador_salida = logging.StreamHandler()

    manejador_salida.setFormatter(
        FormateadorJson()
    )

    _listener_logs = QueueListener(
        _cola_logs,
        manejador_salida,
        respect_handler_level=True,
    )

    _listener_logs.start()

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
    cliente_id: int | None = None,
    cuenta_origen_id: int | None = None,
) -> None:

    logger.info(
        mensaje,
        extra={
            "componente": componente,
            "evento": evento,
            "trace_id": trace_id,
            "transaccion_id": transaccion_id,
            "cliente_id": cliente_id,
            "cuenta_origen_id": cuenta_origen_id,
        },
    )
