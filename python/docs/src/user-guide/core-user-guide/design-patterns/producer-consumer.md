# Producer-Consumer Pattern

This pattern models a task queue:

- one or more **producers** publish work items
- one or more **consumers** process those items
- a **collector** gathers results

It is useful for parallel workflows and distributed task scheduling.

## Message Types and Topics

```python
from dataclasses import dataclass

TASKS_TOPIC = "tasks"
RESULTS_TOPIC = "results"


@dataclass
class WorkItem:
    task_id: str
    payload: str


@dataclass
class WorkResult:
    task_id: str
    worker: str
    output: str
```

## Consumer Agent

Each consumer subscribes to `TASKS_TOPIC`, processes work, and publishes a `WorkResult` to `RESULTS_TOPIC`.

```python
import asyncio

from autogen_core import MessageContext, RoutedAgent, TopicId, message_handler, type_subscription


@type_subscription(topic_type=TASKS_TOPIC)
class WorkerAgent(RoutedAgent):
    @message_handler
    async def handle_work(self, message: WorkItem, ctx: MessageContext) -> None:
        # Simulate variable processing time.
        await asyncio.sleep(0.1)
        result = WorkResult(
            task_id=message.task_id,
            worker=self.id.key,
            output=message.payload.upper(),
        )
        await self.publish_message(result, topic_id=TopicId(type=RESULTS_TOPIC, source="runtime"))
```

## Result Collector

The collector subscribes to `RESULTS_TOPIC` and signals completion when all tasks are processed.

```python
import asyncio

from autogen_core import MessageContext, RoutedAgent, message_handler, type_subscription


@type_subscription(topic_type=RESULTS_TOPIC)
class ResultCollector(RoutedAgent):
    def __init__(self, expected_results: int, done_event: asyncio.Event) -> None:
        super().__init__("Collects worker outputs")
        self._expected_results = expected_results
        self._done_event = done_event
        self.results: list[WorkResult] = []

    @message_handler
    async def handle_result(self, message: WorkResult, ctx: MessageContext) -> None:
        self.results.append(message)
        if len(self.results) >= self._expected_results:
            self._done_event.set()
```

## End-to-End Runtime Example

```python
import asyncio

from autogen_core import SingleThreadedAgentRuntime, TopicId


async def main() -> None:
    work_items = [
        WorkItem(task_id="task-1", payload="draft outline"),
        WorkItem(task_id="task-2", payload="summarize notes"),
        WorkItem(task_id="task-3", payload="extract entities"),
    ]
    done_event = asyncio.Event()

    runtime = SingleThreadedAgentRuntime()

    # Register two consumers for parallel processing.
    await WorkerAgent.register(runtime, "worker_1", lambda: WorkerAgent("Worker 1"))
    await WorkerAgent.register(runtime, "worker_2", lambda: WorkerAgent("Worker 2"))

    # Keep a handle to collector output.
    collector_ref: dict[str, ResultCollector] = {}

    def create_collector() -> ResultCollector:
        collector = ResultCollector(expected_results=len(work_items), done_event=done_event)
        collector_ref["instance"] = collector
        return collector

    await ResultCollector.register(runtime, "collector", create_collector)

    runtime.start()

    # Producer logic: publish tasks.
    for item in work_items:
        await runtime.publish_message(
            item,
            topic_id=TopicId(type=TASKS_TOPIC, source="runtime"),
        )

    # Wait until all items have been consumed and collected.
    await done_event.wait()
    await runtime.stop_when_idle()

    results = collector_ref["instance"].results
    for result in results:
        print(result.task_id, result.worker, result.output)


asyncio.run(main())
```

## Why This Pattern Works Well in Core

- Topic-based routing cleanly decouples producers, consumers, and collectors.
- You can scale consumers horizontally by registering more worker instances.
- The same pattern extends to distributed runtimes with minimal logic changes.

## Variations

- Add a priority field on `WorkItem` and route with separate topic types.
- Add retry metadata and a dead-letter topic for failed work.
- Replace the result collector with a downstream agent that performs aggregation or storage.
