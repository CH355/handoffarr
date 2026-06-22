"""Small logging helpers for endpoint/runtime timings."""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Iterator

logger = logging.getLogger("handoffarr.perf")


@contextmanager
def timed(operation: str, **fields: object) -> Iterator[None]:
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        details = " ".join(f"{key}={value}" for key, value in fields.items())
        logger.info("timing operation=%s elapsed_ms=%.2f %s", operation, elapsed_ms, details)


def trace(operation: str, **fields: object) -> None:
    details = " ".join(f"{key}={value}" for key, value in fields.items())
    logger.info("trace operation=%s %s", operation, details)
