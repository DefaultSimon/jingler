import logging
from logging import Formatter
from logging.handlers import TimedRotatingFileHandler

from jinglebot.configuration import DATA_DIR

LOG_DIR_NAME = "logs"
LOG_FILE_NAME = "jingler.log"

LOG_DIR_PATH = DATA_DIR / LOG_DIR_NAME
LOG_FILE_PATH = LOG_DIR_PATH / LOG_FILE_NAME

CONSOLE_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"
FILE_FORMAT = "%(asctime)s:%(levelname)s:%(name)s[%(funcName)s]: %(message)s"

if not LOG_DIR_PATH.exists():
    LOG_DIR_PATH.mkdir(parents=True)

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

sh = logging.StreamHandler()
sh.setLevel(logging.INFO)
sh.setFormatter(Formatter(CONSOLE_FORMAT))

fh = TimedRotatingFileHandler(
    LOG_FILE_PATH, when="W0", encoding="utf8",
)
fh.setLevel(logging.INFO)
fh.setFormatter(Formatter(FILE_FORMAT))

root_logger.addHandler(sh)
root_logger.addHandler(fh)
