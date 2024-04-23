import datetime
import random

from .agent import Agent
from .events import Event, Message, NewMessageEvent, SafetyAssessment, on


class MonitoringAgent(Agent):

    @on(NewMessageEvent)
    async def print_new_message(self, event: Event) -> None:

        source: str = event.message.source
        target: str = event.message.target

        # get current time in readable format
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        print(
            f"""
[{timestamp}]
{source} -> {target}:

{event.message.content}

--------------------------------------------------------
""",
            flush=True,
        )

    @on(SafetyAssessment)
    async def print_safety_message(self, event: Event) -> None:

        safety_msg = event.message.content
        # print a message in red ink
        print("\033[91m [Safety Assessment] " + safety_msg[:80] + "\033[0m", flush=True)


class SafetyAgent(Agent):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, *kwargs)
        self._states = {"Safe", "Not Safe"}

    @on(NewMessageEvent)
    async def assess_safety(self, event: Event) -> None:

        if event.message.source == self.name:
            return

        # choose a random state from _states
        random_state = random.choice(list(self._states))

        reply = SafetyAssessment(
            Message(source=self.name, target="--", content=f'"{event.message.content}" is {random_state}')
        )
        await self.post_event(reply)
