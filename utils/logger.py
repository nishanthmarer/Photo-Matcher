##########################################################################################################################
# Author: Nishanth Marer Prabhu
# fileName: logger.py
# Description: Centralized logging setup for all modules. Creates consistently configured loggers with both console
#              and file output. Each module calls setup_logger() with its name to get a logger that follows the same
#              format, level, and output destinations. Duplicate handler prevention ensures that importing the same
#              module multiple times doesn't produce repeated log lines.
# Year: 2026
###########################################################################################################################

import logging
import sys

from config import LoggingConfig


def setup_logger(name: str, config: LoggingConfig) -> logging.Logger:
    """Create a consistently configured logger for any module.

    If a logger with the given name already has handlers, it is returned as-is to avoid duplicate output.
    This is important because Python's logging module uses a global registry — calling setup_logger() twice
    with the same name would otherwise add duplicate handlers and produce doubled log lines.

    Output goes to both console (stdout) and a log file for post-run debugging.

    Args:
        name: Logger name, typically the module path (e.g., "core.detector", "services.segregator").
        config: Logging configuration (format, date format, file path, level).

    Returns:
        Configured logger instance ready to use.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(config.log_level)

    formatter = logging.Formatter(fmt=config.log_format, datefmt=config.date_format)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(config.log_level)
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(config.log_file, encoding="utf-8")
    file_handler.setLevel(config.log_level)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger