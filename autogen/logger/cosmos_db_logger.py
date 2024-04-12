import logging
import uuid
from typing import TYPE_CHECKING, Any, Dict, TypedDict, Union

from azure.cosmos import CosmosClient

from autogen.logger.base_logger import BaseLogger
from autogen.logger.logger_utils import get_current_ts, to_dict

if TYPE_CHECKING:
    from autogen.agent.conversable_agent import ConversableAgent
    from autogen.wrapper.openai_wrapper import OpenAIWrapper

logger = logging.getLogger(__name__)


class CosmosDBConfig(TypedDict):
    connection_string: str
    database_name: str  # Optional key, hence not enforcing it as mandatory
    container_name: str  # Optional key, hence not enforcing it as mandatory


class CosmosDBLogger(BaseLogger):
    def __init__(self, config: CosmosDBConfig):
        self.config = config
        self.client = CosmosClient.from_connection_string(config["connection_string"])
        self.database_name = config.get("database_name", "AutogenLogging")
        self.database = self.client.get_database_client(self.database_name)
        self.container_name = config.get("container_name", "Logs")
        self.container = self.database.get_container_client(self.container_name)
        self.session_id = str(uuid.uuid4())

    def start(self) -> str:
        try:
            self.database.create_container_if_not_exists(id=self.container_name, partition_key="/session_id")
        except Exception as e:
            logger.error(f"Failed to create or access container {self.container_name}: {e}")
        return self.session_id

    def log_chat_completion(
        self,
        invocation_id: uuid.UUID,
        client_id: int,
        wrapper_id: int,
        request: Dict[str, Any],
        response: Union[str, Dict[str, Any], None],
        is_cached: int,
        cost: float,
        start_time: str,
    ) -> None:
        document = {
            "type": "chat_completion",
            "invocation_id": str(invocation_id),
            "client_id": client_id,
            "wrapper_id": wrapper_id,
            "session_id": self.session_id,
            "request": to_dict(request),
            "response": to_dict(response),
            "is_cached": is_cached,
            "cost": cost,
            "start_time": start_time,
            "end_time": get_current_ts()
        }
        self.container.upsert_item(document)

    def log_new_agent(self, agent: ConversableAgent, init_args: Dict[str, Any]) -> None:
        document = {
            "type": "new_agent",
            "session_id": self.session_id,
            "agent_id": id(agent),
            "agent_name": agent.name,
            "init_args": to_dict(init_args),
            "timestamp": get_current_ts()
        }
        self.container.upsert_item(document)

    def log_new_wrapper(self, wrapper: OpenAIWrapper, init_args: Dict[str, Any]) -> None:
        document = {
            "type": "new_wrapper",
            "session_id": self.session_id,
            "wrapper_id": id(wrapper),
            "init_args": to_dict(init_args),
            "timestamp": get_current_ts()
        }
        self.container.upsert_item(document)

    def log_new_client(self, client: Any, wrapper: OpenAIWrapper, init_args: Dict[str, Any]) -> None:
        document = {
            "type": "new_client",
            "session_id": self.session_id,
            "client_id": id(client),
            "wrapper_id": id(wrapper),
            "client_class": type(client).__name__,
            "init_args": to_dict(init_args),
            "timestamp": get_current_ts()
        }
        self.container.upsert_item(document)

    def stop(self) -> None:
        # Cosmos DB SDK handles connection disposal automatically.
        pass

    def get_connection(self) -> None:
        # Cosmos DB connection management differs from SQLite and is handled by the SDK.
        return None
