"""Structured logging for viznoir MCP server."""

from __future__ import annotations

import logging
import os
import sys

_LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"


def get_logger(name: str) -> logging.Logger:
    """Get a viznoir logger that writes to stderr only.

    stdout is reserved for MCP JSON-RPC, so all logging goes to stderr.
    """
    logger = logging.getLogger(f"viznoir.{name}")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        logger.addHandler(handler)
        logger.propagate = False  # prevent duplicate output via root logger
    level = os.environ.get("VIZNOIR_LOG_LEVEL", "WARNING").upper()
    logger.setLevel(getattr(logging, level, logging.WARNING))
    return logger
