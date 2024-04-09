#install Azure Cosmos DB asynchronous I/O packages if you haven't already
pip install azure-cosmos
pip install aiohttp

import pickle
from typing import Any, Optional, Union
from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey
from autogen.cache.abstract_cache_base import AbstractCache

class CosmosDBCache(AbstractCache):
    def __init__(self, seed: Union[str, int], connection_string: Optional[str] = None, database_id: str = "", container_id: str = "", client: Optional[CosmosClient] = None):
        """
        Initialize the CosmosDBCache instance.

        Args:
            seed (Union[str, int]): A seed or namespace for the cache. Used as a partition key.
            connection_string (str): The connection string for the Cosmos DB account. Required if client is not provided.
            database_id (str): The database ID to be used. Required if client is not provided.
            container_id (str): The container ID to be used for caching. Required if client is not provided.
            client (Optional[CosmosClient]): An existing CosmosClient instance to be used for caching.
        """
        self.seed = seed
        if client is None:
            if not connection_string:
                raise ValueError("connection_string must be provided if client is not passed")
            self.client = CosmosClient.from_connection_string(connection_string)
            self.database = self.client.get_database_client(database_id)
        else:
            self.client = client
            self.database = self.client.get_database_client(database_id)
        self.container = database.get_container_client(container_id)

    async def init_container(self):
        """
        Initialize the container for caching, creating it if it doesn't exist.
        """
        if not await self.container.exists():
            await self.database.create_container(id=self.container.id, partition_key=PartitionKey(path='/partitionKey'))

    async def get(self, key: str, default: Optional[Any] = None) -> Optional[Any]:    
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
        except CosmosResourceNotFoundError:
            return default
        except Exception as e:
            # Log the exception or rethrow after logging if needed
            # Consider logging or handling the error appropriately here
            raise e

    async def set(self, key: str, value: Any) -> None:
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
        await self.container.upsert_item(item)

    async def close(self) -> None:
        """
        Close the Cosmos DB client.

        Perform any necessary cleanup, such as closing network connections.
        """
        # The client should be closed if it was created inside this class,
        # otherwise, it's the responsibility of the caller to close it.
        if 'connection_string' in self.__dict__:
            await self.client.close()

    async def __enter__(self):
        """
        Context management entry.

        Returns:
            self: The instance itself.
        """
        await self.init_container()
        return self

    async def __exit__(self, exc_type: Optional[type], exc_value: Optional[Exception], traceback: Optional[TracebackType]) -> None:
        """
        Context management exit.

        Perform cleanup actions such as closing the Cosmos DB client.
        """
        await self.close()
