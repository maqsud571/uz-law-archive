import logging
import sys

logger = logging.getLogger("rag")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("[%(asctime)s] %(message)s")
handler.setFormatter(formatter)

logger.addHandler(handler)