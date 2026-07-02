# ============================================================================
# utils/logger.py
# ----------------------------------------------------------------------------
# APPLICATION LOGGER — one place that configures logging for the whole app.
#
# Writes timestamped lines to logs/app.log, e.g.:
#   2026-07-02 21:40:11 | INFO     | Book added: 'Dune' (id=3)
#   2026-07-02 21:41:02 | ERROR    | DB error [execute_non_query]: ...
#
# What gets logged:
#   - Database errors                          (from database/connection.py)
#   - User actions: Book Added / Deleted /
#     Issued / Returned                        (from the service layer)
#
# Usage anywhere:
#   from utils.logger import logger
#   logger.info("something happened")
#   logger.error("something failed")
# ============================================================================

import logging
import os

# logs/ lives at the project root (one level up from utils/).
_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
_LOG_FILE = os.path.join(_LOG_DIR, "app.log")


def get_logger(name="library"):
    """
    Return the shared application logger, configuring it once.

    Subsequent calls return the same logger without adding duplicate handlers
    (which would otherwise write every line multiple times).
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    os.makedirs(_LOG_DIR, exist_ok=True)
    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(file_handler)
    logger.propagate = False   # don't also print to the root logger/console
    return logger


# A ready-to-use logger instance for convenient importing.
logger = get_logger()
