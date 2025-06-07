"""Logging configuration for the Steam Price Fetcher."""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Default log levels
DEFAULT_CONSOLE_LEVEL = logging.INFO
DEFAULT_FILE_LEVEL = logging.DEBUG

# Log format
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def setup_logger(
    name: str,
    log_dir: Path = None,
    console_level: int = DEFAULT_CONSOLE_LEVEL,
    file_level: int = DEFAULT_FILE_LEVEL,
) -> logging.Logger:
    """Set up and configure a logger with both console and file handlers.

    Args:
        name: Name of the logger, usually the module name
        log_dir: Directory to store log files
        console_level: Logging level for console output
        file_level: Logging level for file output

    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(min(console_level, file_level))

    # Don't add handlers if they already exist (avoid duplicate handlers)
    if logger.handlers:
        return logger

    # Create formatter
    formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (if log_dir is provided)
    if log_dir:
        # Ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)

        # Create timestamp for log filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = log_dir / f'steam_price_{name}_{timestamp}.log'

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(file_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str, log_dir: Path = None) -> logging.Logger:
    """Get or create a logger with the given name.

    Args:
        name: Name of the logger, usually the module name
        log_dir: Directory to store log files

    Returns:
        Logger instance
    """
    # Handle special case for root logger
    if name == '__main__':
        name = 'main'

    return setup_logger(name, log_dir)
