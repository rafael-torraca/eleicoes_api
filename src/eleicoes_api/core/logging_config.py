import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


_STANDARD_LOG_RECORD_KEYS = set(
    logging.makeLogRecord({}).__dict__.keys()
)


class JsonFormatter(logging.Formatter):
    """Formata os logs como objetos JSON."""

    def format(self, record: logging.LogRecord) -> str:
        log_data: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(
                record.created,
                tz=timezone.utc,
            ).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Inclui campos extras informados pelo logger.
        for key, value in record.__dict__.items():
            if (
                key not in _STANDARD_LOG_RECORD_KEYS
                and not key.startswith("_")
            ):
                log_data[key] = value

        # Inclui os detalhes da exceção quando existirem.
        if record.exc_info:
            log_data["exception"] = self.formatException(
                record.exc_info
            )

        return json.dumps(
            log_data,
            ensure_ascii=False,
            default=str,
        )


def configure_logging(environment: str = "development") -> None:
    """Configura o logging centralizado da aplicação."""

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Em desenvolvimento, registramos logs mais detalhados.
    if environment.lower() == "development":
        root_logger.setLevel(logging.DEBUG)
    else:
        root_logger.setLevel(logging.INFO)

    # Evita excesso de mensagens internas das bibliotecas HTTP.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
