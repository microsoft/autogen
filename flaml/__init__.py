from flaml.searcher import CFO, BlendSearch, FLOW2, BlendSearchTuner
from flaml.automl import AutoML, logger_formatter
from flaml.version import __version__
import logging

# Set the root logger.
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
