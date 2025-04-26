from typing import Any, Awaitable, Callable, Iterable, List, Literal, Optional, Union, TypeGuard

from autogen_core.tools import Tool
from pydantic import BaseModel, Field

import azure.ai.projects.models as models
from typing import TypeGuard

ListToolType = Iterable[
    Union[
        Literal[
            "file_search",
            "code_interpreter",
            "bing_grounding",
            "azure_ai_search",
            "azure_function",
            "sharepoint_grounding",
        ],
        models.BingGroundingToolDefinition,
        models.CodeInterpreterToolDefinition,
        models.SharepointToolDefinition,
        models.AzureAISearchToolDefinition,
        models.FileSearchToolDefinition,
        models.AzureFunctionToolDefinition,
        Tool,
        Callable[..., Any],
        Callable[..., Awaitable[Any]],
    ]
]


class AzureAIAgentState(BaseModel):
    """
    Represents the state of an AzureAIAgent that can be saved and loaded.

    This state model keeps track of persistent information about an agent session
    including agent and thread identifiers, message history, and associated resources.

    Attributes:
        type (str): The type identifier for the state object, always "AzureAIAgentState"
        agent_id (Optional[str]): The ID of the Azure AI agent
        thread_id (Optional[str]): The ID of the conversation thread
        initial_message_ids (List[str]): List of message IDs from the initial state
        vector_store_id (Optional[str]): The ID of the associated vector store for file search
        uploaded_file_ids (List[str]): List of IDs for files uploaded to the agent
    """

    type: str = Field(default="AzureAIAgentState")
    agent_id: Optional[str] = None
    thread_id: Optional[str] = None
    initial_message_ids: List[str] = Field(default_factory=list)
    vector_store_id: Optional[str] = None
    uploaded_file_ids: List[str] = Field(default_factory=list)


def has_annotations(obj: Any) -> TypeGuard[list[models.MessageTextUrlCitationAnnotation]]:
    return obj is not None and isinstance(obj, list)
