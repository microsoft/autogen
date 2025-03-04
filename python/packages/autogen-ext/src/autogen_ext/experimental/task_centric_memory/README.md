# Task-Centric Memory
_(EXPERIMENTAL, RESEARCH IN PROGRESS)_

**Task-Centric Memory** is an active research project aimed at giving AI agents the ability to:

* Accomplish general tasks more effectively by learning quickly and continually beyond context-window limitations.
* Remember guidance, corrections, plans, and demonstrations provided by users.
* Learn through the agent's own experience and adapt quickly to changing circumstances.
* Avoid repeating mistakes on tasks that are similar to those previously encountered.

## Installation

Install AutoGen and its extension package as follows:

```bash
pip install -U "autogen-agentchat" "autogen-ext[openai]" "autogen-ext[task-centric-memory]"
```

## Quickstart

<p align="right">
  <img src="../../../../imgs/task_centric_memory_2.png" alt="Description" width="150" align="right" style="margin-left: 10px;">
</p>

This first code snippet runs a basic test to verify that the installation was successful,
as illustrated by the diagram to the right.

```python
import asyncio
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.experimental.task_centric_memory import MemoryController
from autogen_ext.experimental.task_centric_memory.utils import PageLogger


async def main() -> None:
   client = OpenAIChatCompletionClient(model="gpt-4o")
   logger = PageLogger(config={"level": "DEBUG", "path": "./pagelogs/quickstart"})  # Optional, but very useful.
   memory_controller = MemoryController(reset=True, client=client, logger=logger)

   # Add a few task-insight pairs as memories, where an insight can be any string that may help solve the task.
   await memory_controller.add_memo(task="What color do I like?", insight="Deep blue is my favorite color")
   await memory_controller.add_memo(task="What's another color I like?", insight="I really like cyan")
   await memory_controller.add_memo(task="What's my favorite food?", insight="Halibut is my favorite")

   # Retrieve memories for a new task that's related to only two of the stored memories.
   memos = await memory_controller.retrieve_relevant_memos(task="What colors do I like most?")
   print("{} memories retrieved".format(len(memos)))
   for memo in memos:
      print("- " + memo.insight)


asyncio.run(main())
```

<p align="right">
  <img src="../../../../imgs/task_centric_memory_3.png" alt="Description" width="150" align="right" style="margin-left: 10px;">
</p>

This second code example shows one way to incorporate task-centric memory directly into an AutoGen agent,
in this case a subclass of RoutedAgent.
To keep the code short, only the simplest form of memory retrieval is exercised by this agent.

```python

import asyncio
from dataclasses import dataclass
from typing import List

from autogen_core import AgentId, MessageContext, RoutedAgent, SingleThreadedAgentRuntime, message_handler
from autogen_core.models import ChatCompletionClient, LLMMessage, SystemMessage, UserMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.experimental.task_centric_memory import MemoryController
from autogen_ext.experimental.task_centric_memory.utils import PageLogger


@dataclass
class Message:
   content: str


class MemoryEnabledAgent(RoutedAgent):
   def __init__(
           self, description: str, model_client: ChatCompletionClient, memory_controller: MemoryController
   ) -> None:
      super().__init__(description)
      self._model_client = model_client
      self._memory_controller = memory_controller

   @message_handler
   async def handle_message(self, message: Message, context: MessageContext) -> Message:
      # Retrieve relevant memories for the task.
      memos = await self._memory_controller.retrieve_relevant_memos(task=message.content)

      # Format the memories for the model.
      formatted_memos = "Info that may be useful:\n" + "\n".join(["- " + memo.insight for memo in memos])
      print(f"{'-' * 23}Text appended to the user message{'-' * 24}\n{formatted_memos}\n{'-' * 80}")

      # Create the messages for the model with the retrieved memories.
      messages: List[LLMMessage] = [
         SystemMessage(content="You are a helpful assistant."),
         UserMessage(content=message.content, source="user"),
         UserMessage(content=formatted_memos, source="user"),
      ]

      # Call the model with the messages.
      model_result = await self._model_client.create(messages=messages)
      assert isinstance(model_result.content, str)

      # Send the model's response to the user.
      return Message(content=model_result.content)


async def main() -> None:
   client = OpenAIChatCompletionClient(model="gpt-4o")
   logger = PageLogger(config={"level": "DEBUG", "path": "./pagelogs/quickstart2"})  # Optional, but very useful.
   memory_controller = MemoryController(reset=True, client=client, logger=logger)

   # Prepopulate memory to mimic learning from a prior session.
   await memory_controller.add_memo(task="What color do I like?", insight="Deep blue is my favorite color")
   await memory_controller.add_memo(task="What's another color I like?", insight="I really like cyan")
   await memory_controller.add_memo(task="What's my favorite food?", insight="Halibut is my favorite")

   # Create and start an agent runtime.
   runtime = SingleThreadedAgentRuntime()
   runtime.start()

   # Register the agent type.
   await MemoryEnabledAgent.register(
      runtime,
      "memory_enabled_agent",
      lambda: MemoryEnabledAgent(
         "A agent with memory", model_client=client, memory_controller=memory_controller
      ),
   )

   # Send a direct message to the agent.
   request = "What colors do I like most?"
   print("User request: " + request)
   response = await runtime.send_message(
      Message(content=request), AgentId("memory_enabled_agent", "default")
   )
   print("Agent response: " + response.content)

   # Stop the agent runtime.
   await runtime.stop()


asyncio.run(main())
```

## Sample Code

The example above modifies the agent's code.
But it's also possible to add task-centric memory to an agent or multi-agent team _without_ modifying any agent code.
See the [sample code](../../../../../../samples/task_centric_memory) for that and other forms of fast, memory-based learning.


## Architecture

<p align="right">
  <img src="../../../../imgs/task_centric_memory.png" alt="Description" width="300" align="right" style="margin-left: 10px;">
</p>

The block diagram to the right outlines the key components of the architecture in the most general form.
The memory components are shown in blue, and the green blocks represent external components.

The **Memory Controller** implements the fast-learning methods described below,
and manages communication with a **Memory Bank** containing a vector DB and associated structures.

The **Agent or Team** is the AI agent or team of agents to which memory is being added.
The sample code shows how to add task-centric memory to a simple AssistantAgent or a MagenticOneGroupChat team.

The **Apprentice, app, or service** represents the code that instantiates the agent and memory controller,
and routes information between them, effectively wrapping agent and memory into a combined component.
The term _Apprentice_ connotes that this combination uses memory to learn quickly on the job.
The Apprentice class is a minimal reference implementation provided as utility code for illustration and testing,
but most applications will use their own code instead of the Apprentice.

## Memory Creation and Storage

Each stored memory (called a _memo_) contains a text insight and (optionally) a task description.
The insight is intended to help the agent accomplish future tasks that are similar to a prior task.
The memory controller provides methods for different types of learning.
If the user provides advice for solving a given task, the advice is extracted by the model client and stored as an insight.
If the user demonstrates how to perform a task,
the task and demonstration are stored together as an insight used to solve similar but different tasks.
If the agent is given a task (free of side-effects) and some means of determining success or failure,
the memory controller repeats the following learning loop in the background some number of times:

1. Test the agent on the task a few times to check for a failure.
2. If a failure is found, analyze the agent's response in order to:
   1. Diagnose the failure of reasoning or missing information,
   2. Phrase a general piece of advice, such as what a teacher might give to a student,
   3. Temporarily append this advice to the task description,
   4. Return to step 1.
   5. If some piece of advice succeeds in helping the agent solve the task a number of times, add the advice as an insight to memory.
3. For each insight to be stored in memory, an LLM is prompted to generate a set of free-form, multi-word topics related to the insight. Each topic is embedded to a fixed-length vector and stored in a vector DB mapping it to the topic’s related insight.

## Memory Retrieval and Usage

The memory controller provides methods for different types of memory retrieval.
When the agent is given a task, the following steps are performed by the controller:
1. The task is rephrased into a generalized form.
2. A set of free-form, multi-word query topics are generated from the generalized task.
3. A potentially large number of previously stored topics, those most similar to each query topic, are retrieved from the vector DB along with the insights they map to.
4. These candidate memos are filtered by the aggregate similarity of their stored topics to the query topics.
5. In the final filtering stage, an LLM is prompted to validate only those insights that seem potentially useful in solving the task at hand.

Retrieved insights that pass the filtering steps are listed under a heading like
"Important insights that may help solve tasks like this", then appended to the task description before it is passed to the agent as usual.
