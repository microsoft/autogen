from flaml.automl import AutoML
import logging

from flaml.model import BaseEstimator
from flaml.data import get_output_from_log
from flaml.version import __version__

# Set the root logger.
logger = logging.getLogger(__name__)

# Add the console handler.
_ch = logging.StreamHandler()
logger_formatter = logging.Formatter(
    '[%(name)s: %(asctime)s] {%(lineno)d} %(levelname)s - %(message)s',
    '%m-%d %H:%M:%S')
_ch.setFormatter(logger_formatter)
logger.addHandler(_ch)
