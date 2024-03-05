from autogen import ConversableAgent, Agent
from typing import Any, Dict, List


def update_model(
    update_agent: ConversableAgent, preference_data: List[Dict[str, Any]], other_agent: Agent, **kwargs
) -> Dict[str, Any]:
    """Update the model using the preference data and the conversation history.

    Args:
        update_agent (ConversableAgent): the agent who's model will be updated.
        preference_data (List[Dict]): a list of dictionaries containing the preference data.
        other_agent (Agent): the agent who's conversation history will be used to update the model.
        **kwargs: additional keyword arguments for the update model function.

    Returns:
        Dict: a dictionary containing the update stats, messages, and preference data, like so:
        {
            "update_stats": update_model_stats,
            "messages": messages,
            "preference_data": preference_data
        }

    Raises:
        ValueError: If no OpenAIWrapper client is found.
        ValueError: If multiple model clients are registered.
        NotImplementedError: If update_model is not implemented for the underlying client.
    """
    if update_agent.client is None:
        raise ValueError("No OpenAIWrapper client is found.")
    messages = update_agent._oai_messages[other_agent]
    update_model_stats = update_agent.client.update_model(preference_data, messages, **kwargs)
    return {"update_stats": update_model_stats, "messages": messages, "preference_data": preference_data}
