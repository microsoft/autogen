# ruff: noqa: E722
import autogen
from autogen.code_utils import content_str


class MultimodalAgent(autogen.ConversableAgent):
    def __init__(
        self,
        name,
        max_images=1,
        **kwargs,
    ):
        super().__init__(
            name=name,
            **kwargs,
        )
        self.max_images = max_images
        self._reply_func_list = []
        self.register_reply([autogen.Agent, None], MultimodalAgent.generate_mlm_reply)
        self.register_reply([autogen.Agent, None], autogen.ConversableAgent.generate_code_execution_reply)
        self.register_reply([autogen.Agent, None], autogen.ConversableAgent.generate_function_call_reply)
        self.register_reply([autogen.Agent, None], autogen.ConversableAgent.check_termination_and_human_reply)

    def _has_image(self, message):
        if isinstance(message["content"], list):
            for elm in message["content"]:
                if elm.get("type", "") == "image_url":
                    return True
        return False

    def _create_with_images(self, messages, max_images=1, **kwargs):
        # Clone the messages to give context, but remove old screenshots
        history = []
        n_images = 0
        for m in messages[::-1]:
            # Create a shallow copy
            message = {}
            message.update(m)

            # If there's an image, then consider replacing it with a string
            if self._has_image(message):
                n_images += 1
                if n_images > max_images:
                    message["content"] = content_str(message["content"])

            # Prepend the message -- since we are iterating backwards
            history.insert(0, message)
        return self.client.create(messages=history, **kwargs)

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
        response = self._create_with_images(messages=self._oai_system_message + messages, max_images=self.max_images)
        completion = self.client.extract_text_or_completion_object(response)[0]
        return True, completion
