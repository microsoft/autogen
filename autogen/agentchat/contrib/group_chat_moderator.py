from typing import Callable, Dict, Optional, Union, Tuple, List, Any
from autogen import GroupChat, Agent
import logging

logger = logging.getLogger(__name__)


class GroupChatModerator(GroupChat):
    """(Experimental) A variation of the standard GroupChat class, but with an alternate prompting strategy
    that focus on conversation moderation rather than role play. A drop-in replacement for GroupChat."""

    def __init__(
        self,
        agents: List[Agent],
        messages: List[Dict],
        max_round: int = 10,
        admin_name: str = "Admin",
        func_call_filter: bool = True,
        speaker_selection_method: str = "auto",
        allow_repeat_speaker: bool = True,
    ):
        """
        GroupChatModerator uses the same initilization and constructor as GroupChat.
        Please refer to the GroupChat constructor for more information.
        """
        super().__init__(
            agents=agents,
            messages=messages,
            max_round=max_round,
            admin_name=admin_name,
            func_call_filter=func_call_filter,
            speaker_selection_method=speaker_selection_method,
            allow_repeat_speaker=allow_repeat_speaker,
        )

    def select_speaker_msg(self, agents: List[Agent]):
        """Return the system message for selecting the next speaker. This is always the *first* message in the context."""
        return f"""You are moderating a conversation between the following participants:

{self._participant_roles(agents)}

Read the following conversation, then carefully consider who should speak next based on who's input would be most valued in this moment (e.g., to make the most progress on the task). Speakers do not need equal speaking time. You may even ignore non-relevant participants. Your focus is on efficiently driving progress toward task completion.

You must select only one speaker to go next, and you must only return their name (i.e., from the set {[agent.name for agent in agents]})
"""

    def select_speaker_prompt(self, agents: List[Agent]):
        """Return the floating system prompt selecting the next speaker. This is always the *last* message in the context."""
        return f"Read the above conversation, then carefully consider who should speak next based on who's input would be most valued in this moment to make progress on the task. Select the next speaker from {[agent.name for agent in agents]}. Only return their name."
