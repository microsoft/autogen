from agnext.components import RoutedAgent, message_handler
from agnext.components.models import ChatCompletionClient
from agnext.components.models._types import SystemMessage
from agnext.core import MessageContext
from messages import AuditorAlert, AuditText

auditor_prompt = """You are an Auditor in a Marketing team
Audit the text bello and make sure we do not give discounts larger than 10%
If the text talks about a larger than 10% discount, reply with a message to the user saying that the discount is too large, and by company policy we are not allowed.
If the message says who wrote it, add that information in the response as well
In any other case, reply with NOTFORME
---
Input: {input}
---
"""


class AuditAgent(RoutedAgent):
    def __init__(
        self,
        model_client: ChatCompletionClient,
    ) -> None:
        super().__init__("")
        self._model_client = model_client

    @message_handler
    async def handle_user_chat_input(self, message: AuditText, ctx: MessageContext) -> None:
        sys_prompt = auditor_prompt.format(input=message.text)
        completion = await self._model_client.create(messages=[SystemMessage(content=sys_prompt)])
        assert isinstance(completion.content, str)
        if "NOTFORME" in completion.content:
            return
        assert ctx.topic_id is not None
        await self.publish_message(
            AuditorAlert(UserId=message.UserId, auditorAlertMessage=completion.content), topic_id=ctx.topic_id
        )
