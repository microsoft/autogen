"""
core_multiagent_patterns_example.py

Demonstrates multi-agent design patterns in AutoGen:
- Single message & multiple processors (pub/sub)
- Multiple messages & multiple processors (topic routing)
- Collecting results with ClosureAgent
- Direct messaging between agents

To run:
    python core_multiagent_patterns_example.py

Note: Requires OPENAI_API_KEY in environment for OpenAI examples if using LLMs.
"""
import asyncio
from dataclasses import dataclass
from typing import List

try:
    from autogen_core import (
        AgentId, ClosureAgent, ClosureContext, DefaultTopicId, MessageContext, RoutedAgent, SingleThreadedAgentRuntime, TopicId, TypeSubscription, default_subscription, message_handler, type_subscription
    )
except ImportError as e:
    print("Required packages not installed:", e)
    print("Please install autogen-core.")
    exit(1)

@dataclass
class Task:
    task_id: str

@dataclass
class TaskResponse:
    task_id: str
    result: str

# --- Single Message & Multiple Processors ---
@default_subscription
class Processor(RoutedAgent):
    def __init__(self, description: str):
        super().__init__(description)
        self._description = description

    @message_handler
    async def on_task(self, message: Task, ctx: MessageContext) -> None:
        print(f"{self._description} starting task {message.task_id}")
        await asyncio.sleep(2)
        print(f"{self._description} finished task {message.task_id}")

# --- Multiple Messages & Multiple Processors ---
TASK_RESULTS_TOPIC_TYPE = "task-results"
task_results_topic_id = TopicId(type=TASK_RESULTS_TOPIC_TYPE, source="default")

@type_subscription(topic_type="urgent")
class UrgentProcessor(RoutedAgent):
    def __init__(self, description: str):
        super().__init__(description)

    @message_handler
    async def on_task(self, message: Task, ctx: MessageContext) -> None:
        print(f"Urgent processor starting task {message.task_id}")
        await asyncio.sleep(1)
        print(f"Urgent processor finished task {message.task_id}")
        task_response = TaskResponse(task_id=message.task_id, result="Results by Urgent Processor")
        await self.publish_message(task_response, topic_id=task_results_topic_id)

@type_subscription(topic_type="normal")
class NormalProcessor(RoutedAgent):
    def __init__(self, description: str):
        super().__init__(description)

    @message_handler
    async def on_task(self, message: Task, ctx: MessageContext) -> None:
        print(f"Normal processor starting task {message.task_id}")
        await asyncio.sleep(3)
        print(f"Normal processor finished task {message.task_id}")
        task_response = TaskResponse(task_id=message.task_id, result="Results by Normal Processor")
        await self.publish_message(task_response, topic_id=task_results_topic_id)

# --- Collecting Results with ClosureAgent ---
queue: asyncio.Queue = asyncio.Queue()

async def collect_result(_agent: ClosureContext, message: TaskResponse, ctx: MessageContext) -> None:
    await queue.put(message)

# --- Direct Messaging ---
class WorkerAgent(RoutedAgent):
    def __init__(self, description: str):
        super().__init__(description)

    @message_handler
    async def on_task(self, message: Task, ctx: MessageContext) -> TaskResponse:
        print(f"{self.id} starting task {message.task_id}")
        await asyncio.sleep(2)
        print(f"{self.id} finished task {message.task_id}")
        return TaskResponse(task_id=message.task_id, result=f"Results by {self.id}")

class DelegatorAgent(RoutedAgent):
    def __init__(self, description: str, worker_type: str):
        super().__init__(description)
        self.worker_instances = [AgentId(worker_type, f"{worker_type}-1"), AgentId(worker_type, f"{worker_type}-2")]

    @message_handler
    async def on_task(self, message: Task, ctx: MessageContext) -> TaskResponse:
        print(f"Delegator received task {message.task_id}.")
        subtask1 = Task(task_id="task-part-1")
        subtask2 = Task(task_id="task-part-2")
        worker1_result, worker2_result = await asyncio.gather(
            self.send_message(subtask1, self.worker_instances[0]),
            self.send_message(subtask2, self.worker_instances[1])
        )
        combined_result = f"Part 1: {worker1_result.result}, Part 2: {worker2_result.result}"
        task_response = TaskResponse(task_id=message.task_id, result=combined_result)
        return task_response

async def main():
    print("\n--- Single Message & Multiple Processors ---")
    runtime = SingleThreadedAgentRuntime()
    await Processor.register(runtime, "agent_1", lambda: Processor("Agent 1"))
    await Processor.register(runtime, "agent_2", lambda: Processor("Agent 2"))
    runtime.start()
    await runtime.publish_message(Task(task_id="task-1"), topic_id=DefaultTopicId())
    await runtime.stop_when_idle()

    print("\n--- Multiple Messages & Multiple Processors ---")
    runtime = SingleThreadedAgentRuntime()
    await UrgentProcessor.register(runtime, "urgent_processor", lambda: UrgentProcessor("Urgent Processor"))
    await NormalProcessor.register(runtime, "normal_processor", lambda: NormalProcessor("Normal Processor"))
    runtime.start()
    await runtime.publish_message(Task(task_id="normal-1"), topic_id=TopicId(type="normal", source="default"))
    await runtime.publish_message(Task(task_id="urgent-1"), topic_id=TopicId(type="urgent", source="default"))
    await runtime.stop_when_idle()

    print("\n--- Collecting Results with ClosureAgent ---")
    runtime = SingleThreadedAgentRuntime()
    await UrgentProcessor.register(runtime, "urgent_processor", lambda: UrgentProcessor("Urgent Processor"))
    await NormalProcessor.register(runtime, "normal_processor", lambda: NormalProcessor("Normal Processor"))
    CLOSURE_AGENT_TYPE = "collect_result_agent"
    await ClosureAgent.register_closure(
        runtime,
        CLOSURE_AGENT_TYPE,
        collect_result,
        subscriptions=lambda: [TypeSubscription(topic_type=TASK_RESULTS_TOPIC_TYPE, agent_type=CLOSURE_AGENT_TYPE)],
    )
    runtime.start()
    await runtime.publish_message(Task(task_id="normal-1"), topic_id=TopicId(type="normal", source="default"))
    await runtime.publish_message(Task(task_id="urgent-1"), topic_id=TopicId(type="urgent", source="default"))
    await runtime.stop_when_idle()
    while not queue.empty():
        print(await queue.get())

    print("\n--- Direct Messaging ---")
    runtime = SingleThreadedAgentRuntime()
    await WorkerAgent.register(runtime, "worker", lambda: WorkerAgent("Worker Agent"))
    await DelegatorAgent.register(runtime, "delegator", lambda: DelegatorAgent("Delegator Agent", "worker"))
    runtime.start()
    delegator = AgentId("delegator", "default")
    response = await runtime.send_message(Task(task_id="main-task"), recipient=delegator)
    print(f"Final result: {response.result}")
    await runtime.stop_when_idle()

if __name__ == "__main__":
    asyncio.run(main())
