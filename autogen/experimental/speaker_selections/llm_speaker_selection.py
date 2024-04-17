# from typing import List, Optional

# from ..chat_history import ChatHistoryReadOnly

# from ..agent import Agent
# from ..model_client import ModelClient
# from ..speaker_selection import SpeakerSelection

# class RoundRobin(SpeakerSelection):
#     def __init__(self, client: ModelClient,
#                 select_speaker_message_template: str = """You are in a role play game. The following roles are available:
#                 {roles}.
#                 Read the following conversation.
#                 Then select the next role from {agentlist} to play. Only return the role.""",
#                 select_speaker_prompt_template: str = (
#                     "Read the above conversation. Then select the next role from {agentlist} to play. Only return the role."
#                 )


#                  ) -> None:
#         self._model_client = client

#     def select_speaker(self, agents: List[Agent], chat_history: ChatHistoryReadOnly) -> Agent:
