import logging, sys
from pathlib import Path

def configure_logging(log_file: str = "logs/bot.log") -> None:
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, encoding="utf-8"),
    ]
    logging.basicConfig(level=logging.INFO, format=fmt, datefmt=datefmt, handlers=handlers)
    logging.getLogger("httpx").setLevel(logging.INFO)
    logging.getLogger("telegram").setLevel(logging.INFO)
