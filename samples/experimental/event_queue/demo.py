import asyncio
import datetime

import openai
from src.events import Message, NewMessageEvent, default_queue
from src.llm_agent import LLMAgent
from src.monitoring import MonitoringAgent, SafetyAgent
from src.user_agent import UserAgent


async def main() -> None:

    # define a simple chat gpt application
    llm_agent = LLMAgent(name="LLM")
    user_agent = UserAgent(name="User")

    # declare async monitoring and safety agents
    monitoring_agent = MonitoringAgent(name="Monitoring agent")
    await monitoring_agent._register_event_handlers()
    safety_agent = SafetyAgent(name="Safety agent")
    await safety_agent._register_event_handlers()

    for sub in default_queue.subscribers:
        print(sub)
        handlers = default_queue.subscribers[sub]
        for h in handlers:
            print(h)

    message_event1 = NewMessageEvent(
        Message(source=llm_agent.name, target=user_agent.name, content="Hello! How can I assist you today?")
    )
    await llm_agent.post_event(message_event1)


if __name__ == "__main__":
    asyncio.run(main())
