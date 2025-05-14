import os
import sys
from loguru import logger

# Clean up any default handlers
logger.remove()

# Log directory
log_dir = os.path.join(os.path.dirname(__file__), "logs", "JobIntel-gateway-app")
os.makedirs(log_dir, exist_ok=True)

# Console output
logger.add(
    sys.stdout,
    level="DEBUG",
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
)

# File output (rotates at 10 MB, retains for 7 days, compresses old logs)
log_file_path = os.path.join(log_dir, "gateway.log")
logger.add(
    "logs/JobIntel-gateway-app.log",
    rotation="10 MB",
    retention="7 days",
    compression="zip",
    level="DEBUG",
    enqueue=True,
)

logger.debug("📦 JobIntel_gateway logger initialized.")
