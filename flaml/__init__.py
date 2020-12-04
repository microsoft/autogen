from flaml.automl import AutoML
from flaml.model import BaseEstimator
from flaml.data import get_output_from_log

from flaml.version import __version__

import logging
from os.path import join, exists
import datetime as dt
from os import listdir, remove, mkdir
import pathlib
import json

root = pathlib.Path(__file__).parent.parent.absolute() 
jsonfilepath = join(root, "settings.json")

with open(jsonfilepath) as f:
    settings = json.load(f)

logging_level = settings["logging_level"]

if logging_level == "info":
    logging_level = logging.INFO
elif logging_level == "debug":
    logging_level = logging.DEBUG
elif logging_level == "error":
    logging_level = logging.ERROR
elif logging_level == "warning":
    logging_level = logging.WARNING
elif logging_level == "critical":
    logging_level = logging.CRITICAL
else:
    logging_level = logging.NOTSET

keep_max_logfiles = settings["keep_max_logfiles"]

log_dir = join(root, "logs")

if not exists(log_dir):
    mkdir(log_dir)

del_logs = sorted([int(x.split("_")[0]) for x in listdir(log_dir) if ".log" in
 x], reverse=True)[keep_max_logfiles:]

for l in del_logs:
    try:
        remove(join(log_dir, str(l) + "_flaml.log"))
    except Exception as e:
        continue

b = dt.datetime.now()
a = dt.datetime(2020, 4, 1, 0, 0, 0)
secs = int((b-a).total_seconds())
name = str(secs) 

logger = logging.getLogger(__name__)
logger.setLevel(logging_level)
fh = logging.FileHandler(join(log_dir, name + "_" + __name__ + ".log"))
fh.setLevel(logging_level)
ch = logging.StreamHandler()
ch.setLevel(logging_level)
# formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
formatter = logging.Formatter(
    '[%(name)s: %(asctime)s] {%(lineno)d} %(levelname)s - %(message)s',
    '%m-%d %H:%M:%S')
ch.setFormatter(formatter)
fh.setFormatter(formatter)
logger.addHandler(ch)
logger.addHandler(fh)
logger.propagate = True
