# ruff: noqa: E722
import autogen
from autogen.code_utils import content_str


class MultimodalAgent(autogen.ConversableAgent):
    def __init__(
        self,
        name,
        **kwargs,
    ):
        super().__init__(
            name=name,
            **kwargs,
        )
        self._reply_func_list = []
        self.register_reply([autogen.Agent, None], MultimodalAgent.generate_mlm_reply)
        self.register_reply([autogen.Agent, None], autogen.ConversableAgent.generate_code_execution_reply)
        self.register_reply([autogen.Agent, None], autogen.ConversableAgent.generate_function_call_reply)
        self.register_reply([autogen.Agent, None], autogen.ConversableAgent.check_termination_and_human_reply)

    def generate_mlm_reply(
        self,
        messages=None,
        sender=None,
        config=None,
    ):
        """Generate a reply using autogen.oai."""
        if messages is None:
            messages = self._oai_messages[sender]

        # Clone the messages to give context, but remove old screenshots
        history = []
        for i in range(0, len(messages) - 1):
            message = {}
            message.update(messages[i])
            message["content"] = content_str(message["content"])
            history.append(message)
        history.append(messages[-1])

        response = self.client.create(messages=self._oai_system_message + history)
        completion = self.client.extract_text_or_completion_object(response)[0]
        return True, completion
