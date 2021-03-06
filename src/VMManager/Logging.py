import os
import logging
from logging.handlers import TimedRotatingFileHandler

LOG_FILENAME = 'log/vmmanager.log'       # make log name a setting


def setup_logging():
    LOGGER.setLevel(logging.DEBUG)   # make log level a setting
    # Add the log message handler to the logger
    myhandler = TimedRotatingFileHandler(
                                LOG_FILENAME, when='midnight', backupCount=5)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %I:%M:%S %p')
    myhandler.setFormatter(formatter)
    LOGGER.addHandler(myhandler)


if not os.path.isdir("log"):
    os.mkdir("log")
LOGGER = logging.getLogger('vmmgr')
setup_logging()
LOG_FD = open(LOG_FILENAME, 'a')