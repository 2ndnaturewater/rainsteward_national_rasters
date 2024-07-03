import pathlib
import configparser
import logging
import time

def get_config_parser():
    fn = pathlib.Path(__file__).parent / 'config.ini'
    with open(str(fn)) as file:
        config = configparser.ConfigParser()
        config.read_file(file)
        return config

def time_it(method):
    logger = logging.getLogger(__name__)

    def timed(*args, **kw):
        time_start = time.time()
        result = method(*args, **kw)
        time_end = time.time()
        if 'log_time' in kw:
            name = kw.get('log_name', method.__name__.upper())
            kw['log_time'][name] = int((time_end - time_start) * 1000)
        else:
            logger.info("%r  %2.2f ms" % (method.__name__, (time_end - time_start) * 1000))
        return result

    return timed

def contains_zero(*values: list) -> bool:
    return any(item == 0 or item is None for item in values)

def contains_null(*values: list) -> bool:
    return any(item is None for item in values)

def merge_dicts(dict1, dict2):
    res = {**dict1, **dict2}
    return res