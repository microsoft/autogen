from agentchat_nestedchat import AgNestedChat
from autogen_stateflow import AgStateFlow
from promptflow.connections import AzureOpenAIConnection, CustomConnection
from promptflow.core import tool


@tool
def my_python_tool(
    redisConnection: CustomConnection,
    question: str,
    azureOpenAiConnection: AzureOpenAIConnection,
    azureOpenAiModelName: str = "gpt-4-32k",
    autogen_workflow_id: int = 1,
) -> str:
    aoai_api_base = azureOpenAiConnection.api_base
    aoai_api_key: str = azureOpenAiConnection.api_key
    aoai_api_version: str = azureOpenAiConnection.api_version
    OAI_CONFIG_LIST = [
        {
            "model": azureOpenAiModelName,
            "api_key": aoai_api_key,
            "base_url": aoai_api_base,
            "api_type": "azure",
            "api_version": aoai_api_version,
        }
    ]

    redis_url = redisConnection.secrets["redis_url"]
    if autogen_workflow_id == 1:
        ag_workflow = AgStateFlow(config_list=OAI_CONFIG_LIST, redis_url=redis_url)
        res = ag_workflow.chat(question=question)
        return res.summary
    elif autogen_workflow_id == 2:
        ag_workflow = AgNestedChat(config_list=OAI_CONFIG_LIST, redis_url=redis_url)
        res = ag_workflow.chat(question=question)
        return res.summary
    else:
        raise ValueError("Invalid workflow ID")
