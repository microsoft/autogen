from typing import Callable, Dict, List, Optional, Union
from celery import Celery
from autogen.agentchat import ConversableAgent, Agent


def create_task(app: Celery, agent: ConversableAgent) -> Celery.Task:
    @app.task(name=agent.name)
    def _task(messages: List[Dict]):
        # print(messages)
        return agent.generate_reply(messages=messages)

    return _task


class CeleryAgent(ConversableAgent):
    def __init__(self, app: Celery, agent: ConversableAgent) -> None:
        super().__init__(name=agent.name)
        self._app = app
        self._agent = agent
        self._task = create_task(app, agent)
        # TODO: these states should be stored in external memory to be shared
        # across instances of the agent.
        self._oai_messages = agent._oai_messages
        self.reply_at_receive = agent.reply_at_receive

    def reset_consecutive_auto_reply_counter(self, sender: Agent | None = None):
        return self._agent.reset_consecutive_auto_reply_counter(sender)

    def clear_history(self, agent: Agent | None = None):
        return self._agent.clear_history(agent)

    def generate_init_message(self, **context) -> str | Dict:
        return self._agent.generate_init_message(**context)

    def generate_reply(
        self,
        messages: Optional[List[Dict]] = None,
        sender: Optional[Agent] = None,
        exclude: Optional[List[Callable]] = None,
    ) -> Union[str, Dict, None]:
        return self._task.delay(messages=messages).get()
