# Producer-Consumer

The producer-consumer pattern separates the agent that creates work from the
agent that performs it. Work items are published to a queue topic, and a
consumer agent processes them one at a time. Results are published to a
separate topic so another agent can collect or aggregate them.

This pattern is useful for parallel and distributed workflows: the producer
never waits for a result, and the consumer can be scaled by giving each queue
its own topic source.

## Example

The example below uses `autogen-core` only, so it runs without a model client.
The producer publishes five work items, the consumer publishes one result per
item, and the collector gathers the results.

```python
import asyncio
from dataclasses import dataclass

from autogen_core import (
    AgentId,
    MessageContext,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    TopicId,
    TypeSubscription,
    message_handler,
)


@dataclass
class Start:
    count: int


@dataclass
class WorkItem:
    item_id: int
    payload: str


@dataclass
class WorkResult:
    item_id: int
    result: str


class Producer(RoutedAgent):
    def __init__(self, queue: TopicId) -> None:
        super().__init__("producer")
        self._queue = queue

    @message_handler
    async def handle_start(self, message: Start, ctx: MessageContext) -> None:
        for i in range(message.count):
            await self.publish_message(
                WorkItem(item_id=i, payload=f"payload-{i}"), topic_id=self._queue
            )


class Consumer(RoutedAgent):
    def __init__(self, results: TopicId) -> None:
        super().__init__("consumer")
        self._results = results

    @message_handler
    async def handle_work(self, message: WorkItem, ctx: MessageContext) -> None:
        await self.publish_message(
            WorkResult(item_id=message.item_id, result=message.payload.upper()),
            topic_id=self._results,
        )


class Collector(RoutedAgent):
    def __init__(self, sink: list[WorkResult]) -> None:
        super().__init__("collector")
        self._sink = sink

    @message_handler
    async def handle_result(self, message: WorkResult, ctx: MessageContext) -> None:
        self._sink.append(message)


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    queue = TopicId("work", "queue")
    results = TopicId("results", "queue")
    collected: list[WorkResult] = []

    await Producer.register(runtime, "producer", lambda: Producer(queue))
    await Consumer.register(runtime, "consumer", lambda: Consumer(results))
    await Collector.register(runtime, "collector", lambda: Collector(collected))
    await runtime.add_subscription(
        TypeSubscription(topic_type="work", agent_type="consumer")
    )
    await runtime.add_subscription(
        TypeSubscription(topic_type="results", agent_type="collector")
    )

    runtime.start()
    await runtime.send_message(Start(count=5), AgentId("producer", "default"))
    await runtime.stop_when_idle()

    print([(r.item_id, r.result) for r in collected])


asyncio.run(main())
```

Running it prints the results in work-item order:

```text
[(0, 'PAYLOAD-0'), (1, 'PAYLOAD-1'), (2, 'PAYLOAD-2'), (3, 'PAYLOAD-3'), (4, 'PAYLOAD-4')]
```

## How it works

- The producer publishes `WorkItem` to `TopicId("work", "queue")`.
- A type-based subscription maps the `"work"` topic type to the `"consumer"`
  agent type. The topic source (`"queue"`) becomes the agent key, so this
  publishes to `AgentId("consumer", "queue")`.
- The consumer publishes `WorkResult` to `TopicId("results", "queue")`, and
  the collector subscribes to the `"results"` topic type in the same way.
- The runtime queues messages for an agent while it is busy, so messages
  delivered to the same consumer agent are processed in order and the
  consumer never runs two work items concurrently.

## Scaling

A type-based subscription creates one consumer agent per topic source. To
process several queues concurrently, publish to distinct topic sources
(for example `TopicId("work", "queue-a")` and `TopicId("work", "queue-b")`).
Each source gets its own `AgentId("consumer", ...)`, so the runtime can
process the queues without an item being handled twice.

For a distributed deployment, register the producer and consumer agents on
separate runtimes and connect them with the same topic types, as described in
[Distributed Agent Runtime](../framework/distributed-agent-runtime.ipynb).
