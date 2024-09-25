"""
This example shows an implementation of the multi-agent debate pattern
for solving math problems from GSM8K benchmark (https://huggingface.co/datasets/openai/gsm8k).

The example consists of two types of agents: solver agents and an aggregator agent.
The solver agents are connected in a sparse manner following the technique described in
"Improving Multi-Agent Debate with Sparse Communication Topology" (https://arxiv.org/abs/2406.11776).

For example, consider the following connection pattern:

A --- B
|     |
|     |
C --- D

In this pattern, each solver agent is connected to two other solver agents.

The pattern works as follows:
1. The main function sends a math problem to the aggregator agent.
2. The aggregator agent distributes the problem to the solver agents.
3. Each solver agent processes the problem, and publishes a response to all other solver agents.
4. Each solver agent again use the responses from other agents to refine its response, publish a new response.
5. Repeat step 4 for a fixed number of rounds. In the final round, each solver agent publish a final response.
6. The aggregator agent use majority voting to aggregate the final responses from all solver agents to get the final answer, and publishes the answer.

To make the connection dense, modify SolverAgent's handle_response method
to consider all neighbors' responses to use.

To make the connection probabilistic, modify SolverAgent's handle_response method
to sample a random number of neighbors' responses to use.
"""

import asyncio
import logging
import re
import uuid
from dataclasses import dataclass
from typing import Dict, List, Tuple

from autogen_core.application import SingleThreadedAgentRuntime
from autogen_core.base import MessageContext
from autogen_core.components import DefaultSubscription, DefaultTopicId, RoutedAgent, message_handler
from autogen_core.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from common.utils import get_chat_completion_client_from_envs

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@dataclass
class Question:
    content: str


@dataclass
class Answer:
    content: str


@dataclass
class SolverRequest:
    session_id: str
    content: str
    question: str


@dataclass
class IntermediateSolverResponse:
    session_id: str
    content: str
    solver_name: str
    answer: str
    round: int


@dataclass
class FinalSolverResponse:
    session_id: str
    answer: str


class MathSolver(RoutedAgent):
    def __init__(self, model_client: ChatCompletionClient, neighbor_names: List[str], max_round: int) -> None:
        super().__init__("A debator.")
        self._model_client = model_client
        if self.metadata["type"] in neighbor_names:
            raise ValueError("The agent's name cannot be in the list of neighbor names.")
        self._neighbor_names = neighbor_names
        self._memory: Dict[str, List[LLMMessage]] = {}
        self._buffer: Dict[Tuple[str, int], List[IntermediateSolverResponse]] = {}
        self._questions: Dict[str, str] = {}
        self._system_messages = [
            SystemMessage(
                (
                    "You are a helpful assistant with expertise in mathematics and reasoning. "
                    "Your task is to assist in solving a math reasoning problem by providing "
                    "a clear and detailed solution. Limit your output within 100 words, "
                    "and your final answer should be a single numerical number, "
                    "in the form of {{answer}}, at the end of your response. "
                    "For example, 'The answer is {{42}}.'"
                )
            )
        ]
        self._counters: Dict[str, int] = {}
        self._max_round = max_round

    @message_handler
    async def handle_response(self, message: IntermediateSolverResponse, ctx: MessageContext) -> None:
        if message.solver_name not in self._neighbor_names:
            return
        # Add only neighbor's response to the buffer.
        self._buffer.setdefault((message.session_id, message.round), []).append(message)
        # Check if all neighbors have responded.
        if len(self._buffer[(message.session_id, message.round)]) == len(self._neighbor_names):
            question = self._questions[message.session_id]
            # Prepare the prompt for the next question.
            prompt = "These are the solutions to the problem from other agents:\n"
            for resp in self._buffer[(message.session_id, message.round)]:
                prompt += f"One agent solution: {resp.content}\n"
            prompt += (
                "Using the solutions from other agents as additional information, "
                "can you provide your answer to the math problem? "
                f"The original math problem is {question}. "
                "Your final answer should be a single numerical number, "
                "in the form of {{answer}}, at the end of your response."
            )
            # Send the question to the agent itself.
            await self.send_message(
                SolverRequest(content=prompt, session_id=message.session_id, question=question), self.id
            )
            # Clear the buffer.
            self._buffer.pop((message.session_id, message.round))

    @message_handler
    async def handle_request(self, message: SolverRequest, ctx: MessageContext) -> None:
        # Save the question.
        self._questions[message.session_id] = message.question
        # Add the question to the memory.
        self._memory.setdefault(message.session_id, []).append(UserMessage(content=message.content, source="Host"))
        # Make an inference using the model.
        response = await self._model_client.create(self._system_messages + self._memory[message.session_id])
        assert isinstance(response.content, str)
        # Add the response to the memory.
        self._memory[message.session_id].append(
            AssistantMessage(content=response.content, source=self.metadata["type"])
        )
        logger.debug(f"Solver {self.metadata['type']} response: {response.content}")
        # Extract the answer from the response.
        match = re.search(r"\{\{(\-?\d+(\.\d+)?)\}\}", response.content)
        if match is None:
            raise ValueError("The model response does not contain the answer.")
        answer = match.group(1)
        # Increment the counter.
        self._counters[message.session_id] = self._counters.get(message.session_id, 0) + 1
        if self._counters[message.session_id] == self._max_round:
            # If the counter reaches the maximum round, publishes a final response.
            await self.publish_message(
                FinalSolverResponse(answer=answer, session_id=message.session_id), topic_id=DefaultTopicId()
            )
        else:
            # Publish intermediate response.
            await self.publish_message(
                IntermediateSolverResponse(
                    content=response.content,
                    solver_name=self.metadata["type"],
                    answer=answer,
                    session_id=message.session_id,
                    round=self._counters[message.session_id],
                ),
                topic_id=DefaultTopicId(),
            )


class MathAggregator(RoutedAgent):
    def __init__(self, num_solvers: int) -> None:
        super().__init__("Math Aggregator")
        self._num_solvers = num_solvers
        self._responses: Dict[str, List[FinalSolverResponse]] = {}

    @message_handler
    async def handle_question(self, message: Question, ctx: MessageContext) -> None:
        prompt = (
            f"Can you solve the following math problem?\n{message.content}\n"
            "Explain your reasoning. Your final answer should be a single numerical number, "
            "in the form of {{answer}}, at the end of your response."
        )
        session_id = str(uuid.uuid4())
        await self.publish_message(
            SolverRequest(content=prompt, session_id=session_id, question=message.content), topic_id=DefaultTopicId()
        )

    @message_handler
    async def handle_final_solver_response(self, message: FinalSolverResponse, ctx: MessageContext) -> None:
        self._responses.setdefault(message.session_id, []).append(message)
        if len(self._responses[message.session_id]) == self._num_solvers:
            # Find the majority answer.
            answers = [resp.answer for resp in self._responses[message.session_id]]
            majority_answer = max(set(answers), key=answers.count)
            # Publish the aggregated response.
            await self.publish_message(Answer(content=majority_answer), topic_id=DefaultTopicId())
            # Clear the responses.
            self._responses.pop(message.session_id)
            print(f"Aggregated answer: {majority_answer}")


async def main(question: str) -> None:
    # Create the runtime.
    runtime = SingleThreadedAgentRuntime()
    # Register the solver agents.
    # Create a sparse connection: each solver agent has two neighbors.
    # NOTE: to create a dense connection, each solver agent should be connected to all other solver agents.
    await runtime.register(
        "MathSolver1",
        lambda: MathSolver(
            get_chat_completion_client_from_envs(model="gpt-4o-mini"),
            neighbor_names=["MathSolver2", "MathSolver4"],
            max_round=3,
        ),
        lambda: [DefaultSubscription()],
    )
    await runtime.register(
        "MathSolver2",
        lambda: MathSolver(
            get_chat_completion_client_from_envs(model="gpt-4o-mini"),
            neighbor_names=["MathSolver1", "MathSolver3"],
            max_round=3,
        ),
        lambda: [DefaultSubscription()],
    )
    await runtime.register(
        "MathSolver3",
        lambda: MathSolver(
            get_chat_completion_client_from_envs(model="gpt-4o-mini"),
            neighbor_names=["MathSolver2", "MathSolver4"],
            max_round=3,
        ),
        lambda: [DefaultSubscription()],
    )
    await runtime.register(
        "MathSolver4",
        lambda: MathSolver(
            get_chat_completion_client_from_envs(model="gpt-4o-mini"),
            neighbor_names=["MathSolver1", "MathSolver3"],
            max_round=3,
        ),
        lambda: [DefaultSubscription()],
    )
    # Register the aggregator agent.
    await runtime.register("MathAggregator", lambda: MathAggregator(num_solvers=4))

    runtime.start()

    # Send a math problem to the aggregator agent.
    await runtime.publish_message(Question(content=question), topic_id=DefaultTopicId())

    await runtime.stop_when_idle()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("autogen_core").setLevel(logging.DEBUG)
    asyncio.run(
        main(
            "Natalia sold clips to 48 of her friends in April, and then she sold half as many clips in May. How many clips did Natalia sell altogether in April and May?"
        )
    )
    # Expected output: 72
