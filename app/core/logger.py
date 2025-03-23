import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Set up the logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Basic format: time - level - message
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

# Log directory setup
log_dir = Path(__file__).parent.parent.parent / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

# Rotating file handler (2MB max size, keep 5 backup files)
rotating_handler = RotatingFileHandler(
    log_dir / "app.log",
    maxBytes=2 * 1024 * 1024,  # 2MB
    backupCount=5,
    encoding="utf-8",
)
rotating_handler.setFormatter(formatter)
logger.addHandler(rotating_handler)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Example usage
if __name__ == "__main__":
    logger.info("This is an info message")
    logger.error("This is an error message")
    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("An error occurred")
