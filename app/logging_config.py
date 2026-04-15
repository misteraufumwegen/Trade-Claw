"""Structured logging configuration for Trade-Claw."""

import logging
import logging.handlers
import json
import os
from typing import Any
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """Format logs as JSON for structured analysis."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_obj: dict[str, Any] = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add optional fields
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "user_id"):
            log_obj["user_id"] = record.user_id

        if hasattr(record, "session_id"):
            log_obj["session_id"] = record.session_id

        if hasattr(record, "order_id"):
            log_obj["order_id"] = record.order_id

        if hasattr(record, "symbol"):
            log_obj["symbol"] = record.symbol

        if hasattr(record, "action"):
            log_obj["action"] = record.action

        return json.dumps(log_obj)


def setup_logging(
    log_file: str = "trade_claw.log",
    level: str = "INFO",
) -> logging.Logger:
    """
    Configure structured JSON logging.

    Args:
        log_file: Path to log file
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("trade_claw")
    logger.setLevel(getattr(logging, level.upper()))

    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # Console handler (human-readable)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)

    # File handler (rotating, JSON format)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,  # Keep 5 backup files
    )
    file_handler.setLevel(level.upper())
    json_formatter = JSONFormatter()
    file_handler.setFormatter(json_formatter)

    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get or create logger with given name."""
    return logging.getLogger(name)


def log_order_event(
    logger: logging.Logger,
    action: str,
    order_id: str,
    symbol: str,
    session_id: str,
    details: dict[str, Any],
    severity: str = "INFO",
) -> None:
    """
    Log order-related event with context.

    Args:
        logger: Logger instance
        action: Action name (ORDER_SUBMITTED, ORDER_FILLED, etc.)
        order_id: Order ID
        symbol: Trading symbol
        session_id: Broker session ID
        details: Additional details dict
        severity: Log level
    """
    record = logging.LogRecord(
        name=logger.name,
        level=getattr(logging, severity.upper()),
        pathname="",
        lineno=0,
        msg=f"{action}: {symbol}",
        args=(),
        exc_info=None,
    )
    record.order_id = order_id
    record.symbol = symbol
    record.session_id = session_id
    record.action = action

    for key, value in details.items():
        setattr(record, key, value)

    logger.handle(record)


def log_risk_event(
    logger: logging.Logger,
    action: str,
    session_id: str,
    details: dict[str, Any],
    severity: str = "WARNING",
) -> None:
    """
    Log risk-related event.

    Args:
        logger: Logger instance
        action: Action name (RISK_CHECK_FAILED, DRAWDOWN_HALT, etc.)
        session_id: Broker session ID
        details: Additional details dict
        severity: Log level
    """
    record = logging.LogRecord(
        name=logger.name,
        level=getattr(logging, severity.upper()),
        pathname="",
        lineno=0,
        msg=f"{action}",
        args=(),
        exc_info=None,
    )
    record.session_id = session_id
    record.action = action

    for key, value in details.items():
        setattr(record, key, value)

    logger.handle(record)
