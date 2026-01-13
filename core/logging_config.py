import logging
from typing import Dict


DEFAULT_FORMAT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"

# Common logging attributes; anything else on the record is treated as extra
_RESERVED = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
}


class ExtraFormatter(logging.Formatter):
    """Formatter that appends extra dict keys as key=value pairs to the message and colorizes levels."""

    COLORS = {
        "DEBUG": "\033[92m",   # green
        "INFO": "\033[92m",    # green
        "WARNING": "\033[93m", # yellow
        "ERROR": "\033[91m",   # red
        "CRITICAL": "\033[91m"
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        # Colorize levelname
        level = record.levelname
        color = self.COLORS.get(level, "")
        reset = self.RESET if color else ""
        record.levelname = f"{color}{level}{reset}"

        base = super().format(record)
        extras: Dict[str, object] = {
            k: v for k, v in record.__dict__.items() if k not in _RESERVED
        }
        if extras:
            kv = " ".join(f"{k}={v}" for k, v in extras.items())
            return f"{base} | {kv}"
        return base


def setup_logging(
    level: int = logging.INFO,
    sql_level: int = logging.WARNING,
) -> None:
    """
    Configure root logging with a concise format and tone down noisy libraries.
    Safe to call multiple times; only attaches a handler if none exist.
    """
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(ExtraFormatter(DEFAULT_FORMAT))
        root.addHandler(handler)
    root.setLevel(level)

    # Reduce noise from common chatty libraries
    logging.getLogger("sqlalchemy.engine").setLevel(sql_level)
    logging.getLogger("sqlalchemy.pool").setLevel(sql_level)
    logging.getLogger("httpx").setLevel(sql_level)


def get_memory_logger(level: int = logging.INFO) -> logging.Logger:
    """
    Return a dedicated logger for memory-related components.
    Ensures it has a handler so logs appear even if the app overrides root handlers.
    """
    setup_logging()
    logger = logging.getLogger("memory")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(ExtraFormatter(DEFAULT_FORMAT))
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger
