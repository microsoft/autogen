import logging
from typing import Optional

from embedchain.config.base_config import BaseConfig
from embedchain.helpers.json_serializable import JSONSerializable
from embedchain.vectordb.base import BaseVectorDB

logger = logging.getLogger(__name__)


class BaseAppConfig(BaseConfig, JSONSerializable):
    """
    Parent config to initialize an instance of `App`.
    """

    def __init__(
        self,
        log_level: str = "WARNING",
        db: Optional[BaseVectorDB] = None,
        id: Optional[str] = None,
        collect_metrics: bool = True,
        collection_name: Optional[str] = None,
    ):
        """
        Initializes a configuration class instance for an App.
        Most of the configuration is done in the `App` class itself.

        :param log_level: Debug level ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], defaults to "WARNING"
        :type log_level: str, optional
        :param db: A database class. It is recommended to set this directly in the `App` class, not this config,
        defaults to None
        :type db: Optional[BaseVectorDB], optional
        :param id: ID of the app. Document metadata will have this id., defaults to None
        :type id: Optional[str], optional
        :param collect_metrics: Send anonymous telemetry to improve embedchain, defaults to True
        :type collect_metrics: Optional[bool], optional
        :param collection_name: Default collection name. It's recommended to use app.db.set_collection_name() instead,
        defaults to None
        :type collection_name: Optional[str], optional
        """
        self.id = id
        self.collect_metrics = True if (collect_metrics is True or collect_metrics is None) else False
        self.collection_name = collection_name

        if db:
            self._db = db
            logger.warning(
                "DEPRECATION WARNING: Please supply the database as the second parameter during app init. "
                "Such as `app(config=config, db=db)`."
            )

        if collection_name:
            logger.warning("DEPRECATION WARNING: Please supply the collection name to the database config.")
        return

    def _setup_logging(self, log_level):
        logger.basicConfig(format="%(asctime)s [%(name)s] [%(levelname)s] %(message)s", level=log_level)
        self.logger = logger.getLogger(__name__)
