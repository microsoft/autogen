from autogen import oai
from autogen.agentchat.agent import Agent
from autogen.agentchat.assistant_agent import ConversableAgent
from typing import Callable, Dict, Optional, Union, List, Tuple, Any


class AnalysisAgent(ConversableAgent):
    """Text Analysis agent, a subclass of ConversableAgent designed to answer specific questions about text."""
    def __init__(
        self,
        name: str,
        system_message: Optional[str] = "You are an expert in text analysis.",
        llm_config: Optional[Union[Dict, bool]] = None,
        is_termination_msg: Optional[Callable[[Dict], bool]] = None,
        max_consecutive_auto_reply: Optional[int] = None,
        human_input_mode: Optional[str] = "NEVER",
        code_execution_config: Optional[Union[Dict, bool]] = False,
        **kwargs,
    ):
        super().__init__(
            name,
            system_message,
            is_termination_msg,
            max_consecutive_auto_reply,
            human_input_mode,
            code_execution_config=code_execution_config,
            llm_config=llm_config,
            **kwargs,
        )
        self.register_reply(Agent, AnalysisAgent._analyze_text)
        self.use_cache   = False  # 1 to skip LLM calls made previously by relying on cached responses.

    def _analyze_text(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        config: Optional[Any] = None,
    ) -> Tuple[bool, Union[str, Dict, None]]:
        """Analyzes the given text as instructed, and returns the analysis.
        Assumes exactly two messages containing the text to analyze and the analysis instructions respectively.
        See TeachableAgent.analyze for an example of how to use this method."""
        if self.llm_config is False:
            return False, None  # Return if no LLM was provided.
        if messages is None:
            messages = self._oai_messages[sender]  # In case of a direct call.

        # Assemble the message.
        assert len(messages) == 2
        text_to_analyze = 'TEXT:  ' + messages[0]['content']
        analysis_instructions = 'INSTRUCTIONS:  ' + messages[1]['content']
        msg_text = '\n'.join([analysis_instructions, text_to_analyze, analysis_instructions])  # Repeat instructions.
        messages = self._oai_system_message + [{"role": "user", "content": msg_text}]

        # Generate the analysis.
        response = oai.ChatCompletion.create(context=None, messages=messages, use_cache=self.use_cache, **self.llm_config)
        response_text = oai.ChatCompletion.extract_text_or_function_call(response)[0]
        return True, response_text
