import json
import logging
from datetime import datetime, timezone
from typing import Any


class StructuredLogger:
    """
    Logger structuré pour l'observabilité d'Alliance One.
    Écrit les logs au format JSON pour une ingestion facile par Datadog / ELK.
    """

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        if not self.logger.handlers:
            handler = logging.StreamHandler()
            self.logger.addHandler(handler)

    def _log(self, level: str, message: str, **kwargs: Any) -> None:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.upper(),
            "message": message,
            "context": kwargs
        }
        # Dans un environnement de production, ce JSON sera streamé vers stderr/stdout
        # et intercepté par FluentBit ou équivalent.
        print(json.dumps(log_entry))

    def info(self, message: str, **kwargs: Any) -> None:
        self._log("info", message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        self._log("error", message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        self._log("warning", message, **kwargs)


def get_logger(name: str) -> StructuredLogger:
    return StructuredLogger(name)
