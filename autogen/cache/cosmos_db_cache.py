pip install azure-cosmos

import pickle
from typing import Any, Optional, Union
from azure.cosmos import CosmosClient, PartitionKey
from .abstract_cache_base import AbstractCache

class CosmosDBCache(AbstractCache):
    """
    Implementation of AbstractCache using Azure Cosmos DB NoSQL API.

    This class provides a concrete implementation of the AbstractCache
    interface using Azure Cosmos DB for caching data.

    Attributes:
        seed (Union[str, int]): A seed or namespace used as a partition key.
        client (CosmosClient): The Cosmos DB client used for caching.
        container: The container instance used for caching.
    """

    def __init__(self, seed: Union[str, int], connection_string: str, database_id: str, container_id: str):
        """
        Initialize the CosmosDBCache instance.

        Args:
            seed (Union[str, int]): A seed or namespace for the cache. Used as a partition key.
            connection_string (str): The connection string for the Cosmos DB account.
            database_id (str): The database ID to be used.
            container_id (str): The container ID to be used for caching.
        """
        self.seed = seed
        self.client = CosmosClient.from_connection_string(connection_string)
        database = self.client.get_database_client(database_id)
        self.container = database.get_container_client(container_id)
        if not self.container.exists():
            database.create_container(id=container_id, partition_key=PartitionKey(path='/partitionKey'))

    def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:
        """
        Retrieve an item from the Cosmos DB cache.

        Args:
            key (str): The key identifying the item in the cache.
            default (optional): The default value to return if the key is not found.

        Returns:
            The deserialized value associated with the key if found, else the default value.
        """
        try:
            response = self.container.read_item(item=key, partition_key=str(self.seed))
            return pickle.loads(response['data'])
        except Exception:
            return default

    def set(self, key: str, value: Any) -> None:
        """
        Set an item in the Cosmos DB cache.

        Args:
            key (str): The key under which the item is to be stored.
            value: The value to be stored in the cache.

        Notes:
            The value is serialized using pickle before being stored.
        """
        serialized_value = pickle.dumps(value)
        item = {'id': key, 'partitionKey': str(self.seed), 'data': serialized_value}
        self.container.upsert_item(item)

    def close(self) -> None:
        """
        Close the Cosmos DB client.

        Perform any necessary cleanup, such as closing network connections.
        """
        # CosmosClient doesn't require explicit close in the current SDK
        pass

    def __enter__(self):
        """
        Context management entry.

        Returns:
            self: The instance itself.
        """
        return self

    def __exit__(self, exc_type: Optional[Type[BaseException]], exc_value: Optional[BaseException], traceback: Optional[TracebackType]) -> None:
        """
        Context management exit.

        Perform cleanup actions such as closing the Cosmos DB client.
        """
        self.close()
