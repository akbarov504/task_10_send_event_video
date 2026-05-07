import logging
import asyncio

from core.db import init_db
from event_video_uploader import event_video_uploader_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)

logger = logging.getLogger(__name__)

def main():
    logger.info("[APP] Startiang...")

    init_db()

    logging.basicConfig(level=logging.INFO)
    asyncio.run(event_video_uploader_loop())

if __name__ == "__main__":
    main()
