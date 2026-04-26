"""
Multi-Agent Debate Example (GSM8K Math Problem)

This example demonstrates the Multi-Agent Debate pattern using the AutoGen core runtime. Multiple solver agents debate a math problem, exchanging responses in a sparse communication topology, and an aggregator agent collects and aggregates their final answers.

Pattern:
- User sends a math problem to the aggregator agent.
- Aggregator distributes the problem to solver agents.
- Solver agents solve, exchange, and refine their answers over several rounds.
- Aggregator collects final answers and uses majority voting to produce the final answer.

Communication uses topics and subscriptions to implement the sparse topology.

Requirements:
- autogen-core, autogen-ext (install in editable mode)
- OpenAI API key (set OPENAI_API_KEY)

Run with: python python/core_multi_agent_debate_example.py
"""
import asyncio
import re
from dataclasses import dataclass
from typing import Dict, List

from autogen_core import (
    DefaultTopicId,
    MessageContext,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    TypeSubscription,
    default_subscription,
    message_handler,
)
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from autogen_ext.models.openai import OpenAIChatCompletionClient

# ------------------- Message Protocol -------------------
@dataclass
class Question:
    content: str

@dataclass
class Answer:
    content: str

@dataclass
class SolverRequest:
    content: str
    question: str

@dataclass
class IntermediateSolverResponse:
    content: str
    question: str
    answer: str
    round: int

@dataclass
class FinalSolverResponse:
    answer: str

# ------------------- Solver Agent -------------------
@default_subscription
class MathSolver(RoutedAgent):
    def __init__(self, model_client: ChatCompletionClient, topic_type: str, num_neighbors: int, max_round: int) -> None:
        super().__init__("A debator.")
        self._topic_type = topic_type
        self._model_client = model_client
        self._num_neighbors = num_neighbors
        self._history: List[LLMMessage] = []
        self._buffer: Dict[int, List[IntermediateSolverResponse]] = {}
        self._system_messages = [
            SystemMessage(
                content=(
                    "You are a helpful assistant with expertise in mathematics and reasoning. "
                    "Your task is to assist in solving a math reasoning problem by providing "
                    "a clear and detailed solution. Limit your output within 100 words, "
                    "and your final answer should be a single numerical number, "
                    "in the form of {{answer}}, at the end of your response. "
                    "For example, 'The answer is {{42}}.'"
                )
            )
        ]
        self._round = 0
        self._max_round = max_round

    @message_handler
    async def handle_request(self, message: SolverRequest, ctx: MessageContext) -> None:
        self._history.append(UserMessage(content=message.content, source="user"))
        model_result = await self._model_client.create(self._system_messages + self._history)
        assert isinstance(model_result.content, str)
        self._history.append(AssistantMessage(content=model_result.content, source=self.metadata["type"]))
        print(f"{'-'*80}\nSolver {self.id} round {self._round}:\n{model_result.content}")
        match = re.search(r"\{\{(\-?\d+(\.\d+)?)\}\}", model_result.content)
        if match is None:
            raise ValueError("The model response does not contain the answer.")
        answer = match.group(1)
        self._round += 1
        if self._round == self._max_round:
            await self.publish_message(FinalSolverResponse(answer=answer), topic_id=DefaultTopicId())
        else:
            await self.publish_message(
                IntermediateSolverResponse(
                    content=model_result.content,
                    question=message.question,
                    answer=answer,
                    round=self._round,
                ),
                topic_id=DefaultTopicId(type=self._topic_type),
            )

    @message_handler
    async def handle_response(self, message: IntermediateSolverResponse, ctx: MessageContext) -> None:
        self._buffer.setdefault(message.round, []).append(message)
        if len(self._buffer[message.round]) == self._num_neighbors:
            print(
                f"{'-'*80}\nSolver {self.id} round {message.round}:\nReceived all responses from {self._num_neighbors} neighbors."
            )
            prompt = "These are the solutions to the problem from other agents:\n"
            for resp in self._buffer[message.round]:
                prompt += f"One agent solution: {resp.content}\n"
            prompt += (
                "Using the solutions from other agents as additional information, "
                "can you provide your answer to the math problem? "
                f"The original math problem is {message.question}. "
                "Your final answer should be a single numerical number, "
                "in the form of {{answer}}, at the end of your response."
            )
            await self.send_message(SolverRequest(content=prompt, question=message.question), self.id)
            self._buffer.pop(message.round)

# ------------------- Aggregator Agent -------------------
@default_subscription
class MathAggregator(RoutedAgent):
    def __init__(self, num_solvers: int) -> None:
        super().__init__("Math Aggregator")
        self._num_solvers = num_solvers
        self._buffer: List[FinalSolverResponse] = []

    @message_handler
    async def handle_question(self, message: Question, ctx: MessageContext) -> None:
        print(f"{'-'*80}\nAggregator {self.id} received question:\n{message.content}")
        prompt = (
            f"Can you solve the following math problem?\n{message.content}\n"
            "Explain your reasoning. Your final answer should be a single numerical number, "
            "in the form of {{answer}}, at the end of your response."
        )
        print(f"{'-'*80}\nAggregator {self.id} publishes initial solver request.")
        await self.publish_message(SolverRequest(content=prompt, question=message.content), topic_id=DefaultTopicId())

    @message_handler
    async def handle_final_solver_response(self, message: FinalSolverResponse, ctx: MessageContext) -> None:
        self._buffer.append(message)
        if len(self._buffer) == self._num_solvers:
            print(f"{'-'*80}\nAggregator {self.id} received all final answers from {self._num_solvers} solvers.")
            answers = [resp.answer for resp in self._buffer]
            majority_answer = max(set(answers), key=answers.count)
            await self.publish_message(Answer(content=majority_answer), topic_id=DefaultTopicId())
            self._buffer.clear()
            print(f"{'-'*80}\nAggregator {self.id} publishes final answer:\n{majority_answer}")

# ------------------- Main Debate Setup -------------------
async def main():
    runtime = SingleThreadedAgentRuntime()
    model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")

    # Register solver agents
    await MathSolver.register(
        runtime,
        "MathSolverA",
        lambda: MathSolver(
            model_client=model_client,
            topic_type="MathSolverA",
            num_neighbors=2,
            max_round=3,
        ),
    )
    await MathSolver.register(
        runtime,
        "MathSolverB",
        lambda: MathSolver(
            model_client=model_client,
            topic_type="MathSolverB",
            num_neighbors=2,
            max_round=3,
        ),
    )
    await MathSolver.register(
        runtime,
        "MathSolverC",
        lambda: MathSolver(
            model_client=model_client,
            topic_type="MathSolverC",
            num_neighbors=2,
            max_round=3,
        ),
    )
    await MathSolver.register(
        runtime,
        "MathSolverD",
        lambda: MathSolver(
            model_client=model_client,
            topic_type="MathSolverD",
            num_neighbors=2,
            max_round=3,
        ),
    )
    await MathAggregator.register(runtime, "MathAggregator", lambda: MathAggregator(num_solvers=4))

    # Set up sparse topology
    await runtime.add_subscription(TypeSubscription("MathSolverA", "MathSolverD"))
    await runtime.add_subscription(TypeSubscription("MathSolverA", "MathSolverB"))
    await runtime.add_subscription(TypeSubscription("MathSolverB", "MathSolverA"))
    await runtime.add_subscription(TypeSubscription("MathSolverB", "MathSolverC"))
    await runtime.add_subscription(TypeSubscription("MathSolverC", "MathSolverB"))
    await runtime.add_subscription(TypeSubscription("MathSolverC", "MathSolverD"))
    await runtime.add_subscription(TypeSubscription("MathSolverD", "MathSolverC"))
    await runtime.add_subscription(TypeSubscription("MathSolverD", "MathSolverA"))

    # Start debate
    question = "Natalia sold clips to 48 of her friends in April, and then she sold half as many clips in May. How many clips did Natalia sell altogether in April and May?"
    runtime.start()
    await runtime.publish_message(Question(content=question), DefaultTopicId())
    await runtime.stop_when_idle()
    await model_client.close()

if __name__ == "__main__":
    asyncio.run(main())
