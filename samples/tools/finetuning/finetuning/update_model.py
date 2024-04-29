from typing import Any, Dict, List, Protocol

from autogen import Agent, ConversableAgent, ModelClient, OpenAIWrapper


class UpdateableModelClient(ModelClient, Protocol):
    def update_model(
        self, preference_data: List[Dict[str, Any]], inference_messages: List[Dict[str, Any]], **kwargs: Any
    ) -> Dict[str, Any]:
        """Optional method to learn from the preference data, if the model supports learning. Can be omitted.

        Learn from the preference data.

        Args:
            preference_data: The preference data.
            inference_messages: The messages used for inference.
            **kwargs: other arguments.

        Returns:
            Dict of learning stats.
        """
        ...  # pragma: no cover


def _client_wrapper_update_model(
    oai_wrapper_client: OpenAIWrapper,
    preference_data: List[Any],
    inference_messages: List[Dict[str, Any]],
    **kwargs: Any,
) -> Dict[str, Any]:
    """Learn from the preference data.

    update_model is not supported for multiple model clients as it would be ambiguous which client was responsible for the inference messages.

    Args:
        oai_wrapper_client: The OpenAIWrapper client.
        preference_data: The preference data.
        inference_messages: The messages that were used during inference between the agent that is being updated and another agent.
        **kwargs: other arguments.

    Returns:
        Learning stats.

    Raises:
        ValueError: If multiple model clients are registered.
        NotImplementedError: If update_model is not implemented for the client.
    """

    clients = oai_wrapper_client._clients

    if len(clients) != 1:
        raise ValueError("update_model is not supported for multiple model clients.")
    client = clients[0]
    if hasattr(client, "update_model") and callable(getattr(client, "update_model")):
        return client.update_model(preference_data, inference_messages, **kwargs)
    else:
        raise NotImplementedError(f"update_model is not implemented for {client.__class__.__name__}.")


def update_model(
    update_agent: ConversableAgent, preference_data: List[Dict[str, Any]], other_agent: Agent, **kwargs
) -> Dict[str, Any]:
    """Update the model using the preference data and the conversation history.

    Args:
        update_agent (ConversableAgent): the agent whose model will be updated.
        preference_data (List[Dict]): a list of dictionaries containing the preference data.
        other_agent (Agent): the agent whose conversation history will be used to update the model.
        **kwargs: additional keyword arguments for the update model function.

    Returns:
        Dict: a dictionary containing the update stats, inference_messages, and preference data, like so:
        {
            "update_stats": update_model_stats,
            "inference_messages": inference_messages,
            "preference_data": preference_data
        }

    Raises:
        ValueError: If no OpenAIWrapper client is found.
        ValueError: If multiple model clients are registered.
        NotImplementedError: If update_model is not implemented for the underlying client.
    """
    if update_agent.client is None:
        raise ValueError("No OpenAIWrapper client is found.")
    inference_messages = update_agent._oai_messages[other_agent]
    update_model_stats = _client_wrapper_update_model(
        update_agent.client, preference_data, inference_messages, **kwargs
    )
    return {
        "update_stats": update_model_stats,
        "inference_messages": inference_messages,
        "preference_data": preference_data,
    }
