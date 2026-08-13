import logging
import json
import re
from typing import Any, Dict
from contextvars import ContextVar

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="N/A")


def mask_phone_number(phone: str) -> str:
    """Masks phone number for PII compliance (e.g., +919876543210 -> +91****3210)."""
    if not phone or len(phone) < 6:
        return phone
    return f"{phone[:3]}****{phone[-4:]}"


def mask_pii_data(data: Any) -> Any:
    """Recursively masks phone numbers and addresses in dict/list data structures."""
    if isinstance(data, dict):
        masked = {}
        for k, v in data.items():
            if "phone" in k.lower() and isinstance(v, str):
                masked[k] = mask_phone_number(v)
            elif "address" in k.lower() and isinstance(v, str):
                masked[k] = f"{v[:10]}... [MASKED]" if len(v) > 10 else "[MASKED]"
            else:
                masked[k] = mask_pii_data(v)
        return masked
    elif isinstance(data, list):
        return [mask_pii_data(item) for item in data]
    return data


class JSONFormatter(logging.Formatter):
    """Formats logs into structured JSON including correlation ID and PII protection."""

    def __init__(self, service_name: str = "voicekart"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_object: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "service": self.service_name,
            "level": record.levelname,
            "correlation_id": correlation_id_var.get(),
            "logger": record.name,
            "message": record.getMessage(),
        }

        if hasattr(record, "extra_fields"):
            log_object.update(mask_pii_data(record.extra_fields))

        if record.exc_info:
            log_object["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_object, default=str)


def setup_logger(service_name: str, level: str = "INFO") -> logging.Logger:
    """Configures structured JSON logging for a microservice."""
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter(service_name=service_name))
    logger.addHandler(handler)
    logger.propagate = False

    return logger
