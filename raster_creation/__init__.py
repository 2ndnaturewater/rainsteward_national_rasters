import logging
import sys
from raster_creation import common

parser = common.get_config_parser()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

log_file = parser['directories']['log_path']
logger_handler = logging.FileHandler(log_file)
logger_handler.setLevel(logging.DEBUG)
logger_formatter = logging.Formatter('%(asctime)s - %(message)s - %(levelname)s')
logger_handler.setFormatter(logger_formatter)
logger.addHandler(logger_handler)
logger_handler = logging.StreamHandler(sys.stdout)

logger_handler.setLevel(logging.INFO)
logger_formatter = logging.Formatter('%(levelname)s: %(message)s')
logger_handler.setFormatter(logger_formatter)
logger.addHandler(logger_handler)
