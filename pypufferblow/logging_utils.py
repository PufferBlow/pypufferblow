from __future__ import annotations

__all__ = [
    "SDK_LOGGER_NAME",
    "configure_sdk_logging",
    "get_sdk_logger",
]

import logging


SDK_LOGGER_NAME = "pypufferblow"


class _ReadableFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "component"):
            record.component = record.name.rsplit(".", 1)[-1]
        return super().format(record)


def configure_sdk_logging(level: str | int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(SDK_LOGGER_NAME)

    if isinstance(level, str):
        normalized_level = getattr(logging, level.strip().upper(), logging.INFO)
    else:
        normalized_level = level

    logger.setLevel(normalized_level)

    if not any(getattr(handler, "_pypufferblow_handler", False) for handler in logger.handlers):
        handler = logging.StreamHandler()
        handler._pypufferblow_handler = True  # type: ignore[attr-defined]
        handler.setFormatter(
            _ReadableFormatter(
                fmt="%(asctime)s | %(levelname)-7s | %(component)s | %(message)s",
                datefmt="%H:%M:%S",
            )
        )
        logger.addHandler(handler)

    logger.propagate = True
    return logger


def get_sdk_logger(name: str | None = None) -> logging.Logger:
    base_logger = logging.getLogger(SDK_LOGGER_NAME)
    if name:
        return base_logger.getChild(name)
    return base_logger
