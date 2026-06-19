import logging
from typing import Literal

import structlog
from structlog.contextvars import merge_contextvars


def configure_logging(environment: Literal["local", "test", "production"]) -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    processors: list[structlog.typing.Processor] = [
        merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]

    if environment == "local":
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
