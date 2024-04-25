# Install Azure Cosmos DB SDK if not already

import pickle
from typing import Any, Optional, TypedDict, Union

from azure.cosmos import CosmosClient, PartitionKey, exceptions
from azure.cosmos.exceptions import CosmosResourceNotFoundError

from autogen.cache.abstract_cache_base import AbstractCache


class CosmosDBConfig(TypedDict, total=False):
    connection_string: str
    database_id: str
    container_id: str
    cache_seed: Optional[Union[str, int]]
    client: Optional[CosmosClient]


class CosmosDBCache(AbstractCache):
    """
    Synchronous implementation of AbstractCache using Azure Cosmos DB NoSQL API.

    This class provides a concrete implementation of the AbstractCache
    interface using Azure Cosmos DB for caching data, with synchronous operations.

    Attributes:
        seed (Union[str, int]): A seed or namespace used as a partition key.
        client (CosmosClient): The Cosmos DB client used for caching.
        container: The container instance used for caching.
    """

    def __init__(self, seed: Union[str, int], cosmosdb_config: CosmosDBConfig):
        """
        Initialize the CosmosDBCache instance.

        Args:
            seed (Union[str, int]): A seed or namespace for the cache, used as a partition key.
            connection_string (str): The connection string for the Cosmos DB account.
            container_id (str): The container ID to be used for caching.
            client (Optional[CosmosClient]): An existing CosmosClient instance to be used for caching.
        """
        self.seed = str(seed)
        self.client = cosmosdb_config.get("client") or CosmosClient.from_connection_string(
            cosmosdb_config["connection_string"]
        )
        database_id = cosmosdb_config.get("database_id", "autogen_cache")
        self.database = self.client.get_database_client(database_id)
        container_id = cosmosdb_config.get("container_id")
        self.container = self.database.create_container_if_not_exists(
            id=container_id, partition_key=PartitionKey(path="/partitionKey")
        )

    @classmethod
    def create_cache(cls, seed: Union[str, int], cosmosdb_config: CosmosDBConfig):
        """
        Factory method to create a CosmosDBCache instance based on the provided configuration.
        This method decides whether to use an existing CosmosClient or create a new one.
        """
        if "client" in cosmosdb_config and isinstance(cosmosdb_config["client"], CosmosClient):
            return cls.from_existing_client(seed, **cosmosdb_config)
        else:
            return cls.from_config(seed, cosmosdb_config)

    @classmethod
    def from_config(cls, seed: Union[str, int], cosmosdb_config: CosmosDBConfig):
        return cls(str(seed), cosmosdb_config)

    @classmethod
    def from_connection_string(cls, seed: Union[str, int], connection_string: str, database_id: str, container_id: str):
        config = {"connection_string": connection_string, "database_id": database_id, "container_id": container_id}
        return cls(str(seed), config)

    @classmethod
    def from_existing_client(cls, seed: Union[str, int], client: CosmosClient, database_id: str, container_id: str):
        config = {"client": client, "database_id": database_id, "container_id": container_id}
        return cls(str(seed), config)

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
            return pickle.loads(response["data"])
        except CosmosResourceNotFoundError:
            return default
        except Exception as e:
            # Log the exception or rethrow after logging if needed
            # Consider logging or handling the error appropriately here
            raise e

    def set(self, key: str, value: Any) -> None:
        """
        Set an item in the Cosmos DB cache.

        Args:
            key (str): The key under which the item is to be stored.
            value: The value to be stored in the cache.

        Notes:
            The value is serialized using pickle before being stored.
        """
        try:
            serialized_value = pickle.dumps(value)
            item = {"id": key, "partitionKey": str(self.seed), "data": serialized_value}
            self.container.upsert_item(item)
        except Exception as e:
            # Log or handle exception
            raise e

    def close(self) -> None:
        """
        Close the Cosmos DB client.

        Perform any necessary cleanup, such as closing network connections.
        """
        # CosmosClient doesn"t require explicit close in the current SDK
        # If you created the client inside this class, you should close it if necessary
        pass

    def __enter__(self):
        """
        Context management entry.

        Returns:
            self: The instance itself.
        """
        return self

    def __exit__(self, exc_type: Optional[type], exc_value: Optional[Exception], traceback: Optional[Any]) -> None:
        """
        Context management exit.

        Perform cleanup actions such as closing the Cosmos DB client.
        """
        self.close()
