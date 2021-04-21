import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("BitTorrent")
logger.setLevel(logging.ERROR)

Path("../logs/").mkdir(parents=True, exist_ok=True)
# todo uhrzeit
fh = logging.FileHandler(
    "../logs/tkn_bittorrent_" + datetime.now().strftime("%d_%m_%Y_%H_%M_%S") + ".log"
)
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(message)s")
fh.setFormatter(formatter)
logger.addHandler(fh)
