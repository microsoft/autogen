from typing import Dict, List, Optional, Tuple, Union

from autogen import OpenAIWrapper
from autogen.agentchat import Agent, ConversableAgent
from autogen.agentchat.contrib.vectordb.utils import get_logger

logger = get_logger(__name__)

try:
    from llama_index.core.agent.runner.base import AgentRunner
    from llama_index.core.base.llms.types import ChatMessage
    from llama_index.core.chat_engine.types import AgentChatResponse
except ImportError as e:
    logger.fatal("Failed to import llama-index. Try running 'pip install llama-index'")
    raise e


class LLamaIndexConversableAgent(ConversableAgent):
    def __init__(
        self,
        name: str,
        llama_index_agent: AgentRunner,
        description: Optional[str] = None,
        **kwargs,
    ):
        """
        Args:
            name (str): agent name.
            llama_index_agent (AgentRunner): llama index agent.
                Please override this attribute if you want to reprogram the agent.
            description (str): a short description of the agent. This description is used by other agents
                (e.g. the GroupChatManager) to decide when to call upon this agent.
            **kwargs (dict): Please refer to other kwargs in
                [ConversableAgent](../conversable_agent#__init__).
        """

        if llama_index_agent is None:
            raise ValueError("llama_index_agent must be provided")

        if description is None or description.isspace():
            raise ValueError("description must be provided")

        super().__init__(
            name,
            description=description,
            **kwargs,
        )

        self._llama_index_agent = llama_index_agent

        # Override the `generate_oai_reply`
        self.replace_reply_func(ConversableAgent.generate_oai_reply, LLamaIndexConversableAgent._generate_oai_reply)

        self.replace_reply_func(ConversableAgent.a_generate_oai_reply, LLamaIndexConversableAgent._a_generate_oai_reply)

    def _generate_oai_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[OpenAIWrapper] = None,
    ) -> Tuple[bool, Union[str, Dict, None]]:
        """Generate a reply using autogen.oai."""
        user_message, history = self._extract_message_and_history(messages=messages, sender=sender)

        chatResponse: AgentChatResponse = self._llama_index_agent.chat(message=user_message, chat_history=history)

        extracted_response = chatResponse.response

        return (True, extracted_response)

    async def _a_generate_oai_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[OpenAIWrapper] = None,
    ) -> Tuple[bool, Union[str, Dict, None]]:
        """Generate a reply using autogen.oai."""
        user_message, history = self._extract_message_and_history(messages=messages, sender=sender)

        chatResponse: AgentChatResponse = await self._llama_index_agent.achat(
            message=user_message, chat_history=history
        )

        extracted_response = chatResponse.response

        return (True, extracted_response)

    def _extract_message_and_history(
        self, messages: Optional[List[Dict]] = None, sender: Optional[Agent] = None
    ) -> Tuple[str, List[ChatMessage]]:
        """Extract the message and history from the messages."""
        if not messages:
            messages = self._oai_messages[sender]

        if not messages:
            return "", []

        message = messages[-1].get("content", "")

        history = messages[:-1]
        history_messages: List[ChatMessage] = []
        for history_message in history:
            content = history_message.get("content", "")
            role = history_message.get("role", "user")
            if role:
                if role == "user" or role == "assistant":
                    history_messages.append(ChatMessage(content=content, role=role, additional_kwargs={}))
        return message, history_messages
