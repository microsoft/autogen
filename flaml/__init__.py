from flaml.automl import AutoML
from flaml.version import __version__
import logging

# Set the root logger.
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add the console handler.
_ch = logging.StreamHandler()
logger_formatter = logging.Formatter(
    '[%(name)s: %(asctime)s] {%(lineno)d} %(levelname)s - %(message)s',
    '%m-%d %H:%M:%S')
_ch.setFormatter(logger_formatter)
logger.addHandler(_ch)