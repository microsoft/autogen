from typing import Callable, Dict, Optional, Union, Tuple, List, Any
from autogen import OpenAIWrapper
from autogen import Agent, ConversableAgent
import sys
from autogen.token_count_utils import count_token, get_max_token_limit, num_tokens_from_functions
import copy

try:
    from termcolor import colored
except ImportError:

    def colored(x, *args, **kwargs):
        return x


from autogen.agentchat.contrib.compressible_agent import CompressibleAgent
from autogen.agentchat.groupchat import GroupChat, GroupChatManager


class CompressibleGroupChatManager(GroupChatManager):
    """(In preview) GroupChatManager with compression enabled.

    Structure:
    1. Inherit from GroupChatManager: override the function check_groupchat_status to
        check if the tokens used in groupchat is over the limit, and compress if needed.
    2. Composition with CompressibleAgent: use CompressibleAgent to manage the compression.
    """

    def __init__(
        self,
        groupchat: GroupChat,
        name: Optional[str] = "chat_manager",
        # unlimited consecutive auto reply by default
        max_consecutive_auto_reply: Optional[int] = sys.maxsize,
        human_input_mode: Optional[str] = "NEVER",
        system_message: Optional[str] = "Group chat manager.",
        **kwargs,
    ):
        # a proxy agent for compression
        self.compress_agent = CompressibleAgent(
            name=name,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            human_input_mode=human_input_mode,
            system_message=system_message,
            **kwargs,
        )
        if "compress_config" in kwargs:
            del kwargs["compress_config"]

        super().__init__(
            groupchat=groupchat,
            name=name,
            max_consecutive_auto_reply=max_consecutive_auto_reply,
            human_input_mode=human_input_mode,
            system_message=system_message,
            **kwargs,
        )

        if self.compress_agent.compress_config:
            self.compress_agent.update_system_message(groupchat.select_speaker_msg(groupchat.agents))
            self.init_token_count = self.compress_agent._compute_init_token_count() + count_token(
                groupchat.selector_end_msg(), self.compress_agent.llm_config.get("model")
            )
            trigger_count = self.compress_agent.compress_config["trigger_count"]
            if self.init_token_count >= trigger_count:
                print(
                    f"Warning: trigger_count {trigger_count} is less than the initial token count to select speaker {self.init_token_count}. Compression will be performed at each turn. Please increase trigger_count if this is not desired."
                )

    def check_groupchat_status(self, groupchat: GroupChat) -> bool:
        # disabled if compress_config is False
        if self.compress_agent.compress_config is False:
            return False

        # we will only count the token used by groupmanager
        model = self.compress_agent.llm_config.get("model")
        token_used = self.init_token_count + count_token(groupchat.messages, model)

        # check if the token used is over the limit
        final, compressed_messages = self.compress_agent._manage_history_on_token_limit(
            groupchat.messages, token_used, get_max_token_limit(model), model
        )

        # update the groupchat messages
        if final:
            return True  # terminate
        if compressed_messages is not None:
            groupchat.messages = copy.deepcopy(compressed_messages)
            self.compress_agent._print_compress_info(
                self.init_token_count, token_used, self.init_token_count + count_token(compressed_messages, model)
            )
            # update all agents' messages
            for agent in groupchat.agents:
                agent._oai_messages[self] = self._convert_agent_messages(compressed_messages, agent)

        return False  # do not terminate

    @staticmethod
    def _convert_agent_messages(compressed_messages: List[Dict], agent: Agent) -> List[Dict]:
        """Convert messages to a corresponding agent's view."""
        converted_messages = []
        tmp_messages = copy.deepcopy(compressed_messages)
        for cmsg in tmp_messages:
            if cmsg["role"] == "function" or cmsg["role"] == "system":
                pass  # do nothing
            elif cmsg.get("name", "") == agent.name:
                del cmsg["name"]
                cmsg["role"] = "assistant"
            else:
                cmsg["role"] = "user"

            # if the message is a function call, the role is assistant
            if "function_call" in cmsg:
                cmsg["role"] = "assistant"

            converted_messages.append(cmsg)
        return converted_messages
