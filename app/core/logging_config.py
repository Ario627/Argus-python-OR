import logging
import sys

from app.config import settings

def setup_logger() -> logging.Logger:
    logger = logging.getLogger("argus.optimization")
    if logger.handlers:
        return logger
    logger.setLevel(settings.LOG_LEVEL.upper())
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
    )
    logger.addHandler(handler)
    logger.propagate = False
    return logger

logger = setup_logger()