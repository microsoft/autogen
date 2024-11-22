import json

EXAMPLE = {
    "thought": "**Insights:**\nYour insights on what should be the next interesting agent.\n**Overall Idea:**\nyour reasoning and the overall concept behind the agent design.\n**Implementation:**\ndescribe the implementation step by step.",
    "name": "Name of your proposed agent",
    "code": """def forward(self, taskInfo):
    # Your code here
    return answer
"""
}

# COT = {
#     "thought": "By encouraging the LLM to think step by step rather than directly outputting an answer, chain-of-thought reasoning enables complex problem-solving through intermediate steps. This practice improves the model's ability to handle tasks that require deeper reasoning and provides insight into its decision-making process.",
#     "name": "Chain-of-Thought",
#     "code": """def forward(self, taskInfo):
#     # Instruction for the Chain-of-Thought (CoT) approach
#     # It is an important practice that allows the LLM to think step by step before solving the task.
#     cot_instruction = "Please think step by step and then solve the task."

#     # Instantiate a new LLM agent specifically for CoT
#     # To allow LLM thinking before answering, we need to set an additional output field 'thinking'.
#     cot_agent = LLMAgentBase(['thinking', 'answer'], 'Chain-of-Thought Agent')

#     # Prepare the inputs for the CoT agent
#     # The input should be a list of Info, and the first one is often the taskInfo
#     cot_agent_inputs = [taskInfo]

#     # Get the response from the CoT agent
#     thinking, answer = cot_agent(cot_agent_inputs, cot_instruction)

#     # Return only the final answer
#     return answer
# """
# }


COT = {
    "thought": "By encouraging the LLM to think step by step rather than directly outputting an answer, chain-of-thought reasoning enables complex problem-solving through intermediate steps. This practice improves the model's ability to handle tasks that require deeper reasoning and provides insight into its decision-making process.",
    "name": "Chain-of-Thought",
    "code": """def forward(self, task, model_client_kwargs):
    import asyncio
    import logging
    import json
    from dataclasses import dataclass
    import sys
    from autogen_core.application import SingleThreadedAgentRuntime
    from autogen_core.base import AgentId, AgentRuntime, MessageContext
    from autogen_core.components import DefaultTopicId, RoutedAgent, message_handler, ClosureAgent, DefaultSubscription
    from autogen_core.components.models import (
        ChatCompletionClient,
        LLMMessage,
        SystemMessage,
        UserMessage,
    )
    from autogen_ext.models import AzureOpenAIChatCompletionClient
    from typing import List
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider

    token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")

    # Create an AzureOpenAI model client.
    model_client = AzureOpenAIChatCompletionClient(
        model=model_client_kwargs['model'],
        api_version=model_client_kwargs['api_version'],
        azure_endpoint=model_client_kwargs['azure_endpoint'],
        azure_ad_token_provider=token_provider,
        model_capabilities={
            "vision": True,
            "function_calling": True,
            "json_output": True,
        },
    )

    # Define message types as data classes
    @dataclass
    class ChainOfThoughtTask:
        task: str


    @dataclass
    class FinalResult:
        result: str


    # Define the Chain-of-Thought Agent
    class ChainOfThoughtAgent(RoutedAgent):
        def __init__(self, description: str,
                    model_client: ChatCompletionClient,
                    system_prompt: str,
                    instruction: str,
            ) -> None:
            super().__init__(description)
            self._system_messages: List[LLMMessage] = [
                SystemMessage(
                    content=system_prompt,
                )
            ]
            self._model_client = model_client
            self._instruction = instruction

        @message_handler
        async def handle_task(self, message: ChainOfThoughtTask, ctx: MessageContext) -> None:

            logging.info(f"{self._description} received message: {message.task}")
            user_prompt = message.task + "\\n" + self._instruction
            msgs = self._system_messages + [UserMessage(content=user_prompt, source=self.metadata["type"])]
            model_result = await self._model_client.create(msgs)
            assert isinstance(model_result.content, str)

            await self.publish_message(
                message=FinalResult(model_result.content),
                topic_id=DefaultTopicId(),
            )


    # Define the main function to set up and run the agent system
    async def main():

        # Create a queue to collect final answer
        queue = asyncio.Queue[FinalResult]()
        async def output_result(_runtime: AgentRuntime, id: AgentId, message: FinalResult, ctx: MessageContext) -> None:
            await queue.put(message)

        # Initialize the agent runtime
        runtime = SingleThreadedAgentRuntime()

        # Create the chain-of-thought agent
        agent_id = AgentId("COTAgent", "default")
        cot_instruction = "Please think step by step and then solve the task."
        await ChainOfThoughtAgent.register(
            runtime, "COTAgent", lambda: ChainOfThoughtAgent(
                description='Chain-of-Thought Agent',
                model_client=model_client,
                system_prompt="You are a helpful assistant. Directly answer the question. Keep it very concise.",
                instruction=cot_instruction,
            )
        )
        # Create closure agent to collect final output result
        await ClosureAgent.register(runtime, "output_result", output_result, subscriptions=lambda: [DefaultSubscription()])

        # Start the runtime, and publish the first message
        runtime.start()
        initial_message = ChainOfThoughtTask(task=task)
        await runtime.send_message(initial_message, agent_id) # publish_message

        # Keep processing messages until idle.
        await runtime.stop_when_idle()

        # Return the first answer from the queue
        return (await queue.get()).result

    return asyncio.run(main())
"""
}

COT_SC = {
    "thought": "While an LLM can arrive at the correct answer, its reasoning may vary. By repeatedly asking the same question with high temperature settings, we can generate different reasoning paths. We then combine multiple answers from these Chain-of-Thought (CoT) agents to produce a more accurate final answer through ensembling.",
    "name": "Self-Consistency with Chain-of-Thought",
    "code": """def forward(self, task, model_client_kwargs):
    import asyncio
    import logging
    import json
    from dataclasses import dataclass
    import sys
    from autogen_core.application import SingleThreadedAgentRuntime
    from autogen_core.base import AgentId, AgentRuntime, MessageContext
    from autogen_core.components import DefaultTopicId, RoutedAgent, message_handler, ClosureAgent, DefaultSubscription
    from autogen_core.components.models import (
        ChatCompletionClient,
        LLMMessage,
        SystemMessage,
        UserMessage,
    )
    from typing import List
    from autogen_ext.models import AzureOpenAIChatCompletionClient
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider

    token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")

    # Create an AzureOpenAI model client.
    model_client = AzureOpenAIChatCompletionClient(
        model=model_client_kwargs['model'],
        api_version=model_client_kwargs['api_version'],
        azure_endpoint=model_client_kwargs['azure_endpoint'],
        azure_ad_token_provider=token_provider,
        model_capabilities={
            "vision": True,
            "function_calling": True,
            "json_output": True,
        },
    )

    @dataclass
    class WorkerTask:
        task: str
        previous_results: List[str]


    @dataclass
    class WorkerTaskResult:
        result: str


    @dataclass
    class UserTask:
        task: str


    @dataclass
    class FinalResult:
        result: str


    class WorkerAgent(RoutedAgent):
        def __init__(
            self,
            model_client: ChatCompletionClient,
            instruction: str,
        ) -> None:
            super().__init__(description="Worker Agent")
            self._model_client = model_client
            self._instruction = instruction

        @message_handler
        async def handle_task(self, message: WorkerTask, ctx: MessageContext) -> WorkerTaskResult:
            user_prompt = message.task + "\\n" + self._instruction

            if message.previous_results:
                # If previous results are provided, we need to synthesize them to create a single prompt.
                # system_prompt = "You have been provided with a set of responses from various open-source models to the latest user query. Your task is to synthesize these responses into a single, high-quality response. It is crucial to critically evaluate the information provided in these responses, recognizing that some of it may be biased or incorrect. Your response should not simply replicate the given answers but should offer a refined, accurate, and comprehensive reply to the instruction. Ensure your response is well-structured, coherent, and adheres to the highest standards of accuracy and reliability.\\n\\nResponses from models:"
                system_prompt = "Given all the solutions, reason over them carefully and provide a final answer."
                system_prompt += "\\n" + "\\n\\n".join([f"{i+1}. {r}" for i, r in enumerate(message.previous_results)])
                model_result = await self._model_client.create(
                    [SystemMessage(system_prompt), UserMessage(content=user_prompt, source="user")]
                )
            else:
                # If no previous results are provided, we can simply pass the user query to the model.
                model_result = await self._model_client.create([UserMessage(content=user_prompt, source="user")])
            assert isinstance(model_result.content, str)
            print(f"{'-'*80}\\nWorker-{self.id}:\\n{model_result.content}")
            return WorkerTaskResult(result=model_result.content)


    class OrchestratorAgent(RoutedAgent):
        def __init__(
            self,
            model_client: ChatCompletionClient,
            worker_agent_types: List[str],
            num_layers: int,
        ) -> None:
            super().__init__(description="Aggregator Agent")
            self._model_client = model_client
            self._worker_agent_types = worker_agent_types
            self._num_layers = num_layers


        @message_handler
        async def handle_task(self, message: UserTask, ctx: MessageContext) -> FinalResult:
            print(f"{'-'*80}\\nOrchestrator-{self.id}:\\nReceived task: {message.task}")
            # Create task for the first layer.
            worker_task = WorkerTask(task=message.task, previous_results=[])
            # Iterate over layers.
            for i in range(self._num_layers):
                # Assign workers for this layer.
                worker_ids = [
                    AgentId(worker_type, f"{self.id.key}/layer_{i}/worker_{j}")
                    for j, worker_type in enumerate(self._worker_agent_types)
                ]
                # Dispatch tasks to workers.
                print(f"{'-'*80}\\nOrchestrator-{self.id}:\\nDispatch to workers at layer {i}")
                results = await asyncio.gather(*[self.send_message(worker_task, worker_id) for worker_id in worker_ids])
                print(f"{'-'*80}\\nOrchestrator-{self.id}:\\nReceived results from workers at layer {i}")
                # Prepare task for the next layer.
                worker_task = WorkerTask(task=message.task, previous_results=[r.result for r in results])
            # Perform final aggregation.
            print(f"{'-'*80}\\nOrchestrator-{self.id}:\\nPerforming final aggregation")
            # system_prompt = "You have been provided with a set of responses from various open-source models to the latest user query. Your task is to synthesize these responses into a single, high-quality response. It is crucial to critically evaluate the information provided in these responses, recognizing that some of it may be biased or incorrect. Your response should not simply replicate the given answers but should offer a refined, accurate, and comprehensive reply to the instruction. Ensure your response is well-structured, coherent, and adheres to the highest standards of accuracy and reliability.\\n\\nResponses from models:"
            system_prompt = "Given all the above solutions, reason over them carefully and provide a final answer."
            system_prompt += "\\n" + "\\n\\n".join([f"{i+1}. {r}" for i, r in enumerate(worker_task.previous_results)])
            model_result = await self._model_client.create(
                [SystemMessage(system_prompt), UserMessage(content=message.task, source="user")]
            )
            assert isinstance(model_result.content, str)
            return FinalResult(result=model_result.content)

    # Define the main function to set up and run the agent system
    async def main():

        # Initialize the agent runtime
        runtime = SingleThreadedAgentRuntime()

        # Create the agents
        cot_instruction = "Please think step by step and then solve the task."
        await WorkerAgent.register(
            runtime, "worker", lambda: WorkerAgent(model_client=model_client, instruction=cot_instruction)
        )
        await OrchestratorAgent.register(
            runtime,
            "orchestrator",
            lambda: OrchestratorAgent(
                model_client=model_client, worker_agent_types=["worker"] * 5, num_layers=1
            ),
        )

        # Start the runtime, and publish the first message
        runtime.start()
        result = await runtime.send_message(UserTask(task=task), AgentId("orchestrator", "default"))

        # Return the result
        return result.result

    return asyncio.run(main())
"""
}

Reflexion = {
    "thought": "To enhance its performance, an LLM can iteratively improve its answer based on feedback. By reflecting on its previous attempts and incorporating feedback, the model can refine its reasoning and provide a more accurate solution.",
    "name": "Self-Refine (Reflexion)",
    "code": '''def forward(self, task, model_client_kwargs):
    import asyncio
    import json
    import logging
    import re
    import sys
    import uuid
    from dataclasses import dataclass
    from typing import Dict, List, Union
    from autogen_core.base import MessageContext, TopicId, AgentId, AgentRuntime
    from autogen_core.components import RoutedAgent, default_subscription, message_handler, TypeSubscription
    from autogen_core.components.models import (
        AssistantMessage,
        ChatCompletionClient,
        LLMMessage,
        SystemMessage,
        UserMessage,
    )
    from autogen_core.application import SingleThreadedAgentRuntime
    from autogen_core.components import DefaultTopicId, RoutedAgent, message_handler, ClosureAgent
    from autogen_ext.models import AzureOpenAIChatCompletionClient
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider

    token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")

    # Create an AzureOpenAI model client.
    model_client = AzureOpenAIChatCompletionClient(
        model=model_client_kwargs['model'],
        api_version=model_client_kwargs['api_version'],
        azure_endpoint=model_client_kwargs['azure_endpoint'],
        azure_ad_token_provider=token_provider,
        model_capabilities={
            "vision": True,
            "function_calling": True,
            "json_output": True,
        },
    )

    @dataclass
    class WritingTask:
        task: str


    @dataclass
    class WritingResult:
        task: str
        answer: str
        review: str


    @dataclass
    class ReviewTask:
        session_id: str
        writing_task: str
        answer_scratchpad: str
        answer: str


    @dataclass
    class ReviewResult:
        review: str
        session_id: str
        approved: bool


    @default_subscription
    class WorkerAgent(RoutedAgent):
        "An agent that performs writing tasks."

        def __init__(self,
                    model_client: ChatCompletionClient,
                    instruction: str,
        ) -> None:
            super().__init__("A helpful assistant")
            self._system_messages: List[LLMMessage] = [
                SystemMessage(
                    content="""You are a helpful assistant. Work with the critic to improve your answer.
                    Make sure to directly answer the question. Keep it very concise.
                    Respond using the following format:

    Thoughts: <Your comments>
    Answer: <Your answer>
    """,
                )
            ]
            self._model_client = model_client
            self._session_memory: Dict[str, List[WritingTask | ReviewTask | ReviewResult]] = {}
            self._instruction = instruction

        @message_handler
        async def handle_writing_task(self, message: WritingTask, ctx: MessageContext) -> None:
            # Store the messages in a temporary memory for this request only.
            session_id = str(uuid.uuid4())
            self._session_memory.setdefault(session_id, []).append(message)
            # Generate a response using the chat completion API.
            response = await self._model_client.create(
                self._system_messages + [UserMessage(content=message.task + self._instruction, source=self.metadata["type"])],
                cancellation_token=ctx.cancellation_token,
            )
            assert isinstance(response.content, str)
            # Extract the answer from the response.
            answer = self._extract_answer(response.content)
            # Create a review task.
            review_task = ReviewTask(
                session_id=session_id,
                writing_task=message.task,
                answer_scratchpad=response.content,
                answer=answer,
            )
            # Store the review task in the session memory.
            self._session_memory[session_id].append(review_task)
            # Publish a review task.
            await self.publish_message(review_task, topic_id=TopicId("default", self.id.key))

        @message_handler
        async def handle_review_result(self, message: ReviewResult, ctx: MessageContext) -> None:
            # Store the review result in the session memory.
            self._session_memory[message.session_id].append(message)
            # Obtain the request from previous messages.
            review_request = next(
                m for m in reversed(self._session_memory[message.session_id]) if isinstance(m, ReviewTask)
            )
            assert review_request is not None
            # Check if the is approved.
            if message.approved:
                # Publish the writing result.
                await self.publish_message(
                    WritingResult(
                        answer=review_request.answer,
                        task=review_request.writing_task,
                        review=message.review,
                    ),
                    topic_id=TopicId("result", self.id.key),
                )
                print("Writing Result:")
                print("-" * 80)
                print(f"Task:\\n{review_request.writing_task}")
                print("-" * 80)
                print(f"Answer:\\n{review_request.answer}")
                print("-" * 80)
                print(f"Review:\\n{message.review}")
                print("-" * 80)
            else:
                # Create a list of LLM messages to send to the model.
                messages: List[LLMMessage] = [*self._system_messages]
                for m in self._session_memory[message.session_id]:
                    if isinstance(m, ReviewResult):
                        messages.append(UserMessage(content=m.review, source="Reviewer"))
                    elif isinstance(m, ReviewTask):
                        messages.append(AssistantMessage(content=m.answer_scratchpad, source="Worker"))
                    elif isinstance(m, WritingTask):
                        messages.append(UserMessage(content=m.task, source="User"))
                    else:
                        raise ValueError(f"Unexpected message type: {m}")
                # Generate a revision using the chat completion API.
                response = await self._model_client.create(messages, cancellation_token=ctx.cancellation_token)
                assert isinstance(response.content, str)
                # Extract the answer from the response.
                answer = self._extract_answer(response.content)
                # Create a new review task.
                review_task = ReviewTask(
                    session_id=message.session_id,
                    writing_task=review_request.writing_task,
                    answer_scratchpad=response.content,
                    answer=answer,
                )
                # Store the review task in the session memory.
                self._session_memory[message.session_id].append(review_task)
                # Publish a new review task.
                await self.publish_message(review_task, topic_id=TopicId("default", self.id.key))


        def _extract_answer(self, text: str) -> Union[str, None]:
            pattern = "(?<=Answer: ).*"
            # Search for the pattern in the markdown text
            match = re.search(pattern, text, re.DOTALL)
            # Extract the language and code block if a match is found
            if match:
                return match.group(0)
            return None

    @default_subscription
    class ReviewerAgent(RoutedAgent):
        """An agent that critiques tasks."""

        def __init__(self, model_client: ChatCompletionClient) -> None:
            super().__init__("A critic agent.")
            self._system_messages: List[LLMMessage] = [
                SystemMessage(
                    content="""You are a critic. Review answers and criticize on where it might be wrong.
    Respond using the following JSON format:
    {
        "correctness": "<Your comments>",
        "approval": "<APPROVE or REVISE>",
        "suggested_changes": "<Your comments>"
    }
    """,
                )
            ]
            self._session_memory: Dict[str, List[ReviewTask | ReviewResult]] = {}
            self._model_client = model_client

        @message_handler
        async def handle_review_task(self, message: ReviewTask, ctx: MessageContext) -> None:
            # Format the prompt for the review.
            # Gather the previous feedback if available.
            previous_feedback = ""
            if message.session_id in self._session_memory:
                previous_review = next(
                    (m for m in reversed(self._session_memory[message.session_id]) if isinstance(m, ReviewResult)),
                    None,
                )
                if previous_review is not None:
                    previous_feedback = previous_review.review
            # Store the messages in a temporary memory for this request only.
            self._session_memory.setdefault(message.session_id, []).append(message)
            prompt = f"""The problem statement is: {message.writing_task}
    The answer is:
    ```
    {message.answer}
    ```

    Previous feedback:
    {previous_feedback}

    Please review the answer. If previous feedback was provided, see if it was addressed.
    """
            # Generate a response using the chat completion API.
            response = await self._model_client.create(
                self._system_messages + [UserMessage(content=prompt, source=self.metadata["type"])],
                cancellation_token=ctx.cancellation_token,
                json_output=True,
            )
            assert isinstance(response.content, str)
            # TODO: use structured generation library e.g. guidance to ensure the response is in the expected format.
            # Parse the response JSON.
            review = json.loads(response.content)
            # Construct the review text.
            review_text = "Review:\\n" + "\\n".join([f"{k}: {v}" for k, v in review.items()])
            approved = review["approval"].lower().strip() == "approve"
            result = ReviewResult(
                review=review_text,
                session_id=message.session_id,
                approved=approved,
            )
            # Store the review result in the session memory.
            self._session_memory[message.session_id].append(result)
            # Publish the review result.
            await self.publish_message(result, topic_id=TopicId("default", self.id.key))


    # Define the main function to set up and run the agent system
    async def main():
        # Create a queue to collect final answer
        queue = asyncio.Queue[WritingResult]()
        async def output_result(_runtime: AgentRuntime, id: AgentId, message: WritingResult, ctx: MessageContext) -> None:
            await queue.put(message)

        # Initialize the agent runtime
        runtime = SingleThreadedAgentRuntime()

        # Create agents
        await ReviewerAgent.register(
            runtime, "ReviewerAgent", lambda: ReviewerAgent(model_client=model_client)
        )
        cot_instruction = "Please think step by step and then solve the task."
        await WorkerAgent.register(
            runtime, "WorkerAgent", lambda: WorkerAgent(model_client=model_client, instruction=cot_instruction)
        )
        # Create closure agent to collect final output result
        result_topic = TypeSubscription(topic_type="result", agent_type="output_result")
        await ClosureAgent.register(runtime, "output_result", output_result, subscriptions=lambda: [result_topic])

        # Start the runtime, and publish the first message
        runtime.start()
        await runtime.publish_message(
            message=WritingTask(task=task),
            topic_id=DefaultTopicId(),
        )

        # Keep processing messages until idle.
        await runtime.stop_when_idle()

        # Return the first answer from the queue
        print(f"queue {queue}")
        return (await queue.get()).answer
    
    return asyncio.run(main())
'''
}

LLM_debate = {
    "thought": "By letting different LLMs debate with each other, we can leverage their diverse perspectives to find better solutions for tasks.",
    "name": "LLM Debate",
    "code": '''def forward(self, task, model_client_kwargs):
    import asyncio
    import json
    import logging
    import re
    import sys
    import uuid
    from dataclasses import dataclass
    from typing import Dict, List, Union
    from autogen_core.base import MessageContext, TopicId, AgentId, AgentRuntime
    from autogen_core.components import RoutedAgent, default_subscription, message_handler, TypeSubscription
    from autogen_core.components.models import (
        AssistantMessage,
        ChatCompletionClient,
        LLMMessage,
        SystemMessage,
        UserMessage,
    )
    from autogen_core.application import SingleThreadedAgentRuntime
    from autogen_core.components import DefaultTopicId, RoutedAgent, message_handler, ClosureAgent
    from autogen_ext.models import AzureOpenAIChatCompletionClient
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider

    token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")

    # Create an AzureOpenAI model client.
    model_client = AzureOpenAIChatCompletionClient(
        model=model_client_kwargs['model'],
        api_version=model_client_kwargs['api_version'],
        azure_endpoint=model_client_kwargs['azure_endpoint'],
        azure_ad_token_provider=token_provider,
        model_capabilities={
            "vision": True,
            "function_calling": True,
            "json_output": True,
        },
    )
    
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

    @default_subscription
    class Solver(RoutedAgent):
        def __init__(self, model_client: ChatCompletionClient, topic_type: str, num_neighbors: int, max_round: int) -> None:
            super().__init__("A debator.")
            self._topic_type = topic_type
            self._model_client = model_client
            self._num_neighbors = num_neighbors
            self._history: List[LLMMessage] = []
            self._buffer: Dict[int, List[IntermediateSolverResponse]] = {}
            self._system_messages = [
                SystemMessage(
                    (
                        "You are a helpful assistant with expertise in reasoning. "
                        "Your task is to assist in solving a reasoning problem by providing "
                        "a clear and detailed solution. Limit your output within 100 words, "
                        "and your final answer should be a single string."
                    )
                )
            ]
            self._round = 0
            self._max_round = max_round

        @message_handler
        async def handle_request(self, message: SolverRequest, ctx: MessageContext) -> None:
            # Add the question to the memory.
            self._history.append(UserMessage(content=message.content, source="user"))
            # Make an inference using the model.
            model_result = await self._model_client.create(self._system_messages + self._history)
            assert isinstance(model_result.content, str)
            # Add the response to the memory.
            self._history.append(AssistantMessage(content=model_result.content, source=self.metadata["type"]))
            print(f"{'-'*80}\\nSolver {self.id} round {self._round}:\\n{model_result.content}")
            # Increment the counter.
            self._round += 1
            if self._round == self._max_round:
                # If the counter reaches the maximum round, publishes a final response.
                await self.publish_message(FinalSolverResponse(answer=model_result.content), topic_id=DefaultTopicId())
            else:
                # Publish intermediate response to the topic associated with this solver.
                print("publish IntermediateSolverResponse")
                await self.publish_message(
                    IntermediateSolverResponse(
                        content=model_result.content,
                        question=message.question,
                        answer=model_result.content,
                        round=self._round,
                    ),
                    topic_id=DefaultTopicId(type=self._topic_type),
                )

        @message_handler
        async def handle_response(self, message: IntermediateSolverResponse, ctx: MessageContext) -> None:
            # Add neighbor's response to the buffer.
            self._buffer.setdefault(message.round, []).append(message)
            # Check if all neighbors have responded.
            if len(self._buffer[message.round]) == self._num_neighbors:
                print(
                    f"{'-'*80}\\nSolver {self.id} round {message.round}:\\nReceived all responses from {self._num_neighbors} neighbors."
                )
                # Prepare the prompt for the next question.
                prompt = "These are the solutions to the problem from other agents:\\n"
                for resp in self._buffer[message.round]:
                    prompt += f"One agent solution: {resp.content}\\n"
                prompt += (
                    "Using the solutions from other agents as additional information, "
                    "can you provide your answer to the problem? "
                    f"The original problem is {message.question}. "
                    "Your final answer should be a single string."
                )
                # Send the question to the agent itself to solve.
                await self.send_message(SolverRequest(content=prompt, question=message.question), self.id)
                # Clear the buffer.
                self._buffer.pop(message.round)


    @default_subscription
    class Aggregator(RoutedAgent):
        def __init__(self, num_solvers: int) -> None:
            super().__init__("Aggregator")
            self._num_solvers = num_solvers
            self._buffer: List[FinalSolverResponse] = []

        @message_handler
        async def handle_question(self, message: Question, ctx: MessageContext) -> None:
            print(f"{'-'*80}\\nAggregator {self.id} received question:\\n{message.content}")
            prompt = (
                f"Can you solve the following problem?\\n{message.content}\\n"
                "Explain your reasoning. Your final answer should be a single string."
            )
            print(f"{'-'*80}\\nAggregator {self.id} publishes initial solver request.")
            await self.publish_message(SolverRequest(content=prompt, question=message.content), topic_id=DefaultTopicId())

        @message_handler
        async def handle_final_solver_response(self, message: FinalSolverResponse, ctx: MessageContext) -> None:
            self._buffer.append(message)
            if len(self._buffer) == self._num_solvers:
                print(f"{'-'*80}\\nAggregator {self.id} received all final answers from {self._num_solvers} solvers.")
                # Find the majority answer.
                answers = [resp.answer for resp in self._buffer]
                majority_answer = max(set(answers), key=answers.count)
                # Publish the aggregated response.
                await self.publish_message(Answer(content=majority_answer), topic_id=TopicId("result", self.id.key))
                # Clear the responses.
                self._buffer.clear()
                print(f"{'-'*80}\\nAggregator {self.id} publishes final answer:\\n{majority_answer}")


    # Define the main function to set up and run the agent system
    async def main():
        queue = asyncio.Queue[Answer]()
        async def output_result(_runtime: AgentRuntime, id: AgentId, message: Answer, ctx: MessageContext) -> None:
            await queue.put(message)

        runtime = SingleThreadedAgentRuntime()
        await Solver.register(
            runtime,
            "SolverA",
            lambda: Solver(
                model_client=model_client,
                topic_type="SolverA",
                num_neighbors=2,
                max_round=3,
            ),
        )
        await Solver.register(
            runtime,
            "SolverB",
            lambda: Solver(
                model_client=model_client,
                topic_type="SolverB",
                num_neighbors=2,
                max_round=3,
            ),
        )
        await Solver.register(
            runtime,
            "SolverC",
            lambda: Solver(
                model_client=model_client,
                topic_type="SolverC",
                num_neighbors=2,
                max_round=3,
            ),
        )
        await Solver.register(
            runtime,
            "SolverD",
            lambda: Solver(
                model_client=model_client,
                topic_type="SolverD",
                num_neighbors=2,
                max_round=3,
            ),
        )
        await Aggregator.register(runtime, "Aggregator", lambda: Aggregator(num_solvers=4))

        # Subscriptions for topic published to by SolverA.
        await runtime.add_subscription(TypeSubscription("SolverA", "SolverD"))
        await runtime.add_subscription(TypeSubscription("SolverA", "SolverB"))

        # Subscriptions for topic published to by SolverB.
        await runtime.add_subscription(TypeSubscription("SolverB", "SolverA"))
        await runtime.add_subscription(TypeSubscription("SolverB", "SolverC"))

        # Subscriptions for topic published to by SolverC.
        await runtime.add_subscription(TypeSubscription("SolverC", "SolverB"))
        await runtime.add_subscription(TypeSubscription("SolverC", "SolverD"))

        # Subscriptions for topic published to by SolverD.
        await runtime.add_subscription(TypeSubscription("SolverD", "SolverC"))
        await runtime.add_subscription(TypeSubscription("SolverD", "SolverA"))

        # All solvers and the aggregator subscribe to the default topic.

        result_topic = TypeSubscription(topic_type="result", agent_type="output_result")
        await ClosureAgent.register(runtime, "output_result", output_result, subscriptions=lambda: [result_topic])

        runtime.start()
        await runtime.publish_message(Question(content=task), DefaultTopicId())

        # Keep processing messages until idle.
        await runtime.stop_when_idle()

        # Return the answer from the queue
        res = (await queue.get()).content
        print(f"res {res}")
        return res

    return asyncio.run(main())
'''
}

Take_a_step_back = {"thought": "Let LLM first think about the principles involved in solving this task which could be helpful. By understanding the underlying principles, the model can better reason through the problem and provide a more accurate solution.",
                    "name": "Step-back Abstraction",
                    "code": """def forward(self, taskInfo):
        # Instruction for understanding the principles involved in the task
        principle_instruction = "What are the physics, chemistry or biology principles and concepts involved in solving this task? First think step by step. Then list all involved principles and explain them."
        
        # Instruction for solving the task based on the principles
        cot_instruction = "Given the question and the involved principle behind the question, think step by step and then solve the task."
        
        # Instantiate LLM agents
        principle_agent = LLMAgentBase(['thinking', 'principle'], 'Principle Agent')
        cot_agent = LLMAgentBase(['thinking', 'answer'], 'Chain-of-Thought Agent')
        
        # Get the principles involved in the task
        thinking, principle = principle_agent([taskInfo], principle_instruction)

        # Use the principles to solve the task
        thinking, answer = cot_agent([taskInfo, thinking, principle], cot_instruction)
        return answer
"""
                    }

QD = {"thought": "Similar to Quality-Diversity methods, let LLM generate multiple diverse interesting solutions could help. By encouraging the model to explore different reasoning paths, we can increase the chances of finding the best solution.",
      "name": "Quality-Diversity",
      "code": """def forward(self, taskInfo):
    # Instruction for initial reasoning
    cot_initial_instruction = "Please think step by step and then solve the task."

    # Instruction for giving diverse answers
    qd_instruction = "Given previous attempts, try to come up with another interesting way to solve the task."
    cot_agent = LLMAgentBase(['thinking', 'answer'], 'Chain-of-Thought Agent')

    # Instruction for final decision-making based on collected reasoning and answers
    final_decision_instruction = "Given all the above solutions, reason over them carefully and provide a final answer."
    final_decision_agent = LLMAgentBase(['thinking', 'answer'], 'Final Decision Agent', temperature=0.1)
    
    N_max = 3 # Maximum number of attempts

    # Initial attempt
    cot_inputs = [taskInfo]
    possible_answers = []
    thinking, answer = cot_agent(cot_inputs, cot_initial_instruction, 0)

    # Add the answer to the list of possible answers
    possible_answers.extend([thinking, answer])

    for i in range(N_max):
        # Reflect on previous attempts and generate another interesting answer
        cot_inputs.extend([thinking, answer])

        # Generate another interesting answer
        thinking, answer = cot_agent(cot_inputs, qd_instruction, i + 1)
        possible_answers.extend([thinking, answer])

    # Make the final decision based on all generated answers
    thinking, answer = final_decision_agent([taskInfo] + possible_answers, final_decision_instruction)
    return answer
"""
      }

Role_Assignment = {"thought": "Similar to Auto-GPT and expert prompting, we can use dynamic control flow in the design to let the agent decide what expert we should use.",
                   "name": "Dynamic Assignment of Roles",
                   "code": """def forward(self, taskInfo):
        # Instruction for step-by-step reasoning
        cot_instruction = "Please think step by step and then solve the task."
        expert_agents = [LLMAgentBase(['thinking', 'answer'], 'Expert Agent', role=role) for role in ['Reading Comprehension Specialist', 'Logical Reasoning Strategist', 'Multidisciplinary Knowledge Integrator', 'Helpful Assistant']]

        # Instruction for routing the task to the appropriate expert
        routing_instruction = "Given the task, please choose an Expert to answer the question. Choose from: Math Professor, Grade School Teacher, Math Enthusiast."
        routing_agent = LLMAgentBase(['choice'], 'Routing agent')

        # Get the choice of expert to route the task
        choice = routing_agent([taskInfo], routing_instruction)[0]

        if 'professor' in choice.content.lower():
            expert_id = 0
        elif 'teacher' in choice.content.lower():
            expert_id = 1
        elif 'enthusiast' in choice.content.lower():
            expert_id = 2
        else:
            expert_id = 3 # Default to helpful assistant

        thinking, answer = expert_agents[expert_id]([taskInfo], cot_instruction)
        return answer
"""
                   }

system_prompt = lambda formatted_documentation: f"""You are a helpful assistant. You have an expert understanding of the AutoGen framework, and how to use the Python API. The API documentation are as follows: 

{formatted_documentation}

This is the end of the documentation.

Make sure to return in a WELL-FORMED JSON object. Do not add any code blocks around the JSON object."""

base = """# Overview
You are an expert machine learning researcher testing various agentic systems. Your objective is to design building blocks such as prompts and control flows within these systems to solve complex tasks. Your aim is to design an optimal agent performing well on the Reading Comprehension Benchmark Requiring Discrete Reasoning Over Paragraphs (DROP), which assesses the ability to perform discrete reasoning and comprehend detailed information across multiple paragraphs.

## An example question from DROP:

You will be asked to read a passage and answer a question.
Passage:
Non-nationals make up more than half of the population of Bahrain, with immigrants making up about 55% of the overall population.  Of those, the vast majority come from South and Southeast Asia: according to various media reports and government statistics dated between 2005-2009 roughly 290,000 Indians, 125,000 Bangladeshis, 45,000 Pakistanis, 45,000 Filipinos, and 8,000 Indonesians.\nQuestion: What two nationalities had the same number of people living in Bahrain between 2005-2009?
Answer [Not Given]:
Pakistanis and Filipinos 


# The utility code:

```python

Info = namedtuple('Info', ['name', 'author', 'content', 'iteration_idx'])

class AgentArchitecture:
    \"""
    Fill in your code here.
    \"""
    def forward(self, task, model_client_kwargs) -> str:
        \"""
        Placeholder method for processing task information.
        
        Args:
        - task (Info): Task information.
        - model_client_kwargs (Dict): Information for the AzureOpenAIChatCompletionClient
        
        Returns:
        - Answer (str): Your FINAL Answer. Return a string of answers.
        \"""
        pass
```
# Discovered architecture archive
Here is the archive of the discovered architectures:

[ARCHIVE]

The fitness value is the median and 95% Bootstrap Confidence Interval of the correct rate on a validation question set. Your GOAL is to maximize the "fitness".

# Output Instruction and Example:
The first key should be ("thought"), and it should capture your thought process for designing the next function. In the "thought" section, first reason about what should be the next interesting agent to try, then describe your reasoning and the overall concept behind the agent design, and finally detail the implementation steps.
The second key ("name") corresponds to the name of your next agent architecture. 
Finally, the last key ("code") corresponds to the exact “forward()” function in Python code that you would like to try. You must write a COMPLETE CODE in "code": Your code will be part of the entire project, so please implement complete, reliable, reusable code snippets.

Here is an example of the output format for the next agent architecture:

[EXAMPLE]

You must use the exact function interface used above. You need to specify the instruction, input information, and the required output fields for various LLM agents to do their specific part of the architecture. 
Also, it could be helpful to set the LLM’s role to further control the LLM’s response.
DO NOT FORGET the `task` input to LLM if you think it is needed, otherwise LLM will not know about the task.

## WRONG Implementation examples:
Here are some mistakes you may make:

1. This is WRONG: ```

@default_subscription
class WorkerAgent(RoutedAgent):
    def __init__(self):
        pass

    @message_handler
    async def handle_writing_task(self, message: WritingTask, ctx: MessageContext) -> None:
        pass

async def main():
    # Create a queue to collect final answer
    queue = asyncio.Queue[FinalResult]()
    async def output_result(_runtime: AgentRuntime, id: AgentId, message: FinalResult, ctx: MessageContext) -> None:
        await queue.put(message)

    runtime = SingleThreadedAgentRuntime()
    await ReviewerAgent.register(
        runtime, "ReviewerAgent", lambda: ReviewerAgent(model_client=model_client)
    )
    cot_instruction = "Please think step by step and then solve the task."
    await WorkerAgent.register(
        runtime, "WorkerAgent", lambda: WorkerAgent(model_client=model_client, instruction=cot_instruction)
    )
    # Create closure agent to collect final output result
    await ClosureAgent.register(runtime, "output_result", output_result, subscriptions=lambda: [DefaultSubscription()])

    runtime.start()
    await runtime.publish_message(
        message=WritingTask(task=task),
        topic_id=DefaultTopicId(),
    )

    # Keep processing messages until idle.
    await runtime.stop_when_idle()

    # Return the answer from the queue
    return (await queue.get()).answer

return asyncio.run(main())
```
Because the WorkerAgent is subscribed to the `@default_subscription` topic, then there will be conflicts for the ClosureAgent to collect the WritingResult from the same default subscription. Create a new topic using TypeSubscription(topic_type="result", agent_type="output_result") to make this work.

2. This is WRONG: ```
async def main():

    # Initialize the agent runtime
    runtime = SingleThreadedAgentRuntime()

    # Create the agents
    cot_instruction = "Please think step by step and then solve the task."
    await WorkerAgent.register(
        runtime, "worker", lambda: WorkerAgent(model_client=model_client, instruction=cot_instruction)
    )
    await OrchestratorAgent.register(
        runtime,
        "orchestrator",
        lambda: OrchestratorAgent(
            model_client=model_client, worker_agent_types=["worker"] * 5, num_layers=1
        ),
    )

    # Start the runtime, and publish the first message
    runtime.start()
    result = await runtime.send_message(UserTask(task=task), AgentId("orchestrator", "default"))

    # Return the result
    return result.result

return main()
```
The `main()` function needs to be called with `asyncio.run(main())`

3. This is WRONG: ```
# Define the Chain-of-Thought Agent
class ChainOfThoughtAgent(RoutedAgent):
    def __init__(self, description: str,
                model_client: ChatCompletionClient,
                system_prompt: str,
                instruction: str,
        ) -> None:
        super().__init__(description)
        self._system_messages: List[LLMMessage] = [
            SystemMessage(
                content=system_prompt,
            )
        ]
        self._model_client = model_client
        self._instruction = instruction

    @message_handler
    async def handle_task(self, message: ChainOfThoughtTask, ctx: MessageContext) -> FinalResult:

        logging.info(f"{self._description} received message: {message.task}")
        user_prompt = message.task + "\\n" + self._instruction
        msgs = self._system_messages + [UserMessage(content=user_prompt, source=self.metadata["type"])]
        model_result = await self._model_client.create(msgs)
        assert isinstance(model_result.content, str)

        await self.publish_message(
            message=FinalResult(model_result.content),
            topic_id=DefaultTopicId(),
        )
```
Any call with `self.publish_message()` will always return None, so make sure to set the output type of the `handle_task` function as `None`. Example: `async def handle_task(self, message: ChainOfThoughtTask, ctx: MessageContext) -> None:`.

4. This is WRONG: ```
class OrchestratorAgent(RoutedAgent):
    def __init__(
        self,
        model_client: ChatCompletionClient,
        worker_agent_types: List[str],
        num_layers: int,
    ) -> None:
        super().__init__(description="Aggregator Agent")
        self._model_client = model_client
        self._worker_agent_types = worker_agent_types
        self._num_layers = num_layers


    @message_handler
    async def handle_task(self, message: UserTask, ctx: MessageContext) -> None:
        print(f"{'-'*80}\\nOrchestrator-{self.id}:\\nReceived task: {message.task}")
        # Create task for the first layer.
        worker_task = WorkerTask(task=message.task, previous_results=[])
        # Iterate over layers.
        for i in range(self._num_layers):
            # Assign workers for this layer.
            worker_ids = [
                AgentId(worker_type, f"{self.id.key}/layer_{i}/worker_{j}")
                for j, worker_type in enumerate(self._worker_agent_types)
            ]
            # Dispatch tasks to workers.
            print(f"{'-'*80}\\nOrchestrator-{self.id}:\\nDispatch to workers at layer {i}")
            results = await asyncio.gather(*[self.send_message(worker_task, worker_id) for worker_id in worker_ids])
            print(f"{'-'*80}\\nOrchestrator-{self.id}:\\nReceived results from workers at layer {i}")
            # Prepare task for the next layer.
            worker_task = WorkerTask(task=message.task, previous_results=[r.result for r in results])
        # Perform final aggregation.
        print(f"{'-'*80}\\nOrchestrator-{self.id}:\\nPerforming final aggregation")
        # system_prompt = "You have been provided with a set of responses from various open-source models to the latest user query. Your task is to synthesize these responses into a single, high-quality response. It is crucial to critically evaluate the information provided in these responses, recognizing that some of it may be biased or incorrect. Your response should not simply replicate the given answers but should offer a refined, accurate, and comprehensive reply to the instruction. Ensure your response is well-structured, coherent, and adheres to the highest standards of accuracy and reliability.\\n\\nResponses from models:"
        system_prompt = "Given all the above solutions, reason over them carefully and provide a final answer."
        system_prompt += "\\n" + "\\n\\n".join([f"{i+1}. {r}" for i, r in enumerate(worker_task.previous_results)])
        model_result = await self._model_client.create(
            [SystemMessage(system_prompt), UserMessage(content=message.task, source="user")]
        )
        assert isinstance(model_result.content, str)
        return FinalResult(result=model_result.content)
```
Directly returning a message dataclass `FinalResult` requires setting the return type of the `handle_task` function to return `FinalResult`. Example: `async def handle_task(self, message: UserTask, ctx: MessageContext) -> FinalResult:`. 

5. This is WRONG: ```
    # Main orchestration
    async def main():
        runtime = SingleThreadedAgentRuntime()

        # Register agents
        await RetrieverAgent.register(runtime, "retriever_agent")
        await ValidatorAgent.register(runtime, "validator_agent")
        await ReasoningAgent.register(runtime, "reasoning_agent", lambda: ReasoningAgent(model_client=model_client))

        # Start runtime
        runtime.start()
        task_data = task.content if isinstance(task, Info) else task  # Assuming task contains raw question
        await runtime.publish_message(task_data, AgentId("retriever_agent", "default"))

        # Stop when idle
        await runtime.stop_when_idle()

    return asyncio.run(main())
```
The first argument into `publish_message` or `send_message` should not be an `Info` object or any other object. It must be a Message dataclass, which has the format similar to: ```
@dataclass
class Message:
    content: str
```

6. This is WRONG: ```
await ctx.publish(AdaptiveResult(result=response.content), topic_id=ctx.default_topic_id())
```
Publishing should be called with `self.publish_message()`.

7. This is WRONG: ```
await ClosureAgent.register(runtime, "final_collection", collect_final_result, subscriptions=[TypeSubscription("consensus_result", "consensus_agent")])
```
The argument passed to `subscriptions` should not be a list. It should be a lambda function to a list. For example: ```
await ClosureAgent.register(runtime, "final_collection", collect_final_result, subscriptions=lambda: [TypeSubscription("consensus_result", "consensus_agent")])
```

8. This is WRONG: ```
await runtime.publish_message(Task(content='What is the highest mountain in the world?'), topic_id=TypeSubscription("initial_task", "worker_agent").topic_id())
```
The `topic_id` needs to be a `TopicId` with or `DefaultTopicId` object. For example: ```
await runtime.publish_message(Task(content='What is the highest mountain in the world?'), topic_id=TopicId(topic_type, source=self.id.key))
```
or ```
await runtime.publish_message(Task(content='What is the highest mountain in the world?'), topic_id=TopicId(user_topic_type, source=session_id))
```
or ```
await runtime.publish_message(Task(content='What is the highest mountain in the world?'), topic_id=DefaultTopicId())
```

8. This is WRONG: ```
await OrchestratorAgent.register(runtime, "orchestrator")
```
You will encounter this error "TypeError: BaseAgent.register() missing 1 required positional argument: 'factory'". The correct solution is: ```
await OrchestratorAgent.register(runtime, "orchestrator", lambda: OrchestratorAgent())
```

9 This is WRONG: ```
class OrchestratorAgent(RoutedAgent):
    pass
    
async def main():
    await OrchestratorAgent.register(runtime, "orchestrator", lambda: OrchestratorAgent())

    await runtime.publish_message(
        message=DiverseThoughtTask(task='What is the most creative art medium?'),
        topic_id=TopicId("diverse", "orchestrator")
    )
```
You must register subscriptions with the agent runtime through the `add_subscription` method.
```
async def main():
    await OrchestratorAgent.register(runtime, "orchestrator", lambda: OrchestratorAgent())
    await runtime.add_subscription(TypeSubscription("orchestrator_type", "orchestrator"))

    await runtime.publish_message(
        message=DiverseThoughtTask(task='What is the most creative art medium?'),
        topic_id=TopicId(type="orchestrator_type")
    )
```
Or use the `type_subscription()` class decorator on the agent.
```
@type_subscription(topic_type="orchestrator_type")
class OrchestratorAgent(RoutedAgent):
    pass
    
async def main():
    await OrchestratorAgent.register(runtime, "orchestrator", lambda: OrchestratorAgent())

    await runtime.publish_message(
        message=DiverseThoughtTask(task='What is the most creative art medium?'),
        topic_id=TopicId(type="orchestrator_type")
    )
```
Now, you can publish directly to a specific topic through the runtime.

10. This is WRONG: ```
class OrchestratorAgent(RoutedAgent):
    pass
    
async def main():
    await OrchestratorAgent.register(runtime, "orchestrator", lambda: OrchestratorAgent())

    await runtime.publish_message(
        message=DiverseThoughtTask(task='What is the most creative art medium?'),
        topic_id=DefaultTopicId()
    )
```
When there is a single scope of publishing, that is, all agents publish and subscribe to all broadcasted messages, we can use the convenience classes `DefaultTopicId` and `default_subscription()` to simplify our code.
Use the `default_subscription` class decorator on the agent.
```
@default_subscription
class OrchestratorAgent(RoutedAgent):
    pass
    
async def main():
    await OrchestratorAgent.register(runtime, "orchestrator", lambda: OrchestratorAgent())

    await runtime.publish_message(
        message=DiverseThoughtTask(task='What is the most creative art medium?'),
        topic_id=DefaultTopicId()
    )
```

11. This is WRONG: ```
await runtime.publish_message(DiverseThoughtTask(task='Who is the most creative composer?'), AgentId("consensus_agent", "default"))
```
The `publish_message` should publish to a topic. Use `TopicId` or `DefaultTopicId`. For example: ```
await runtime.publish_message(DiverseThoughtTask(task='Who is the most creative composer?'), TopicId("consensus_agent", "default"))
```

## CORRECT Implementation examples:
Here are some correct patterns you should follow:

1. This is CORRECT: ```
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")

# Create an AzureOpenAI model client.
model_client = AzureOpenAIChatCompletionClient(
    model=model_client_kwargs['model'],
    api_version=model_client_kwargs['api_version'],
    azure_endpoint=model_client_kwargs['azure_endpoint'],
    azure_ad_token_provider=token_provider,
    model_capabilities={
        "vision": True,
        "function_calling": True,
        "json_output": True,
    },
)
```
Creating the model client using the model_client_kwargs dictionary.

2. This is CORRECT: ```
    async def main():
        # Create a queue to collect final answer
        queue = asyncio.Queue[WritingResult]()
        async def output_result(_runtime: AgentRuntime, id: AgentId, message: WritingResult, ctx: MessageContext) -> None:
            await queue.put(message)

        # Initialize the agent runtime
        runtime = SingleThreadedAgentRuntime()

        # Create agents

        # Create closure agent to collect final output result
        result_topic = TypeSubscription(topic_type="result", agent_type="output_result")
        await ClosureAgent.register(runtime, "output_result", output_result, subscriptions=lambda: [result_topic])

        # Start the runtime, and publish the first message
        runtime.start()
        await runtime.publish_message()

        # Keep processing messages until idle.
        await runtime.stop_when_idle()

        # Return the first answer from the queue
        print(f"queue {queue}")
        return (await queue.get()).answer
    
    return asyncio.run(main())
```
This is the format for the `main` function. Make sure that when creating a `ClosureAgent`, you have created `queue` from which you can call `return (await queue.get()).answer` at the very end of the `main` function. The datatype of the Queue should be the final message that the agent system publishes to indicate that the system is terminating. 
The `result_topic` should have a unique `topic_type`, which can be called "result".

# Your task
You are deeply familiar with prompting techniques and the agent works from the literature. Your goal is to maximize the specified performance metrics by proposing interestingly new agents.
Observe the discovered agents carefully and think about what insights, lessons, or stepping stones can be learned from them.
Be creative when thinking about the next interesting agent to try. You are encouraged to draw inspiration from related agent papers or academic papers from other research areas.
Use the knowledge from the archive and inspiration from academic literature to propose the next interesting agentic system design.
THINK OUTSIDE THE BOX.
"""

# Documentation: https://github.com/microsoft/autogen/tree/main/python/packages/autogen-core/docs/src/user-guide/core-user-guide


Reflexion_prompt_1 = f""""[EXAMPLE]Carefully review the proposed new architecture and reflect on the following points:

1. **Interestingness**: Assess whether your proposed architecture is interesting or innovative compared to existing methods in the archive. If you determine that the proposed architecture is not interesting, suggest a new architecture that addresses these shortcomings. 
- Make sure to check the difference between the proposed architecture and previous attempts.
- Compare the proposal and the architectures in the archive CAREFULLY, including their actual differences in the implementation.
- Decide whether the current architecture is innovative.
- USE CRITICAL THINKING!

2. **Implementation Mistakes**: Identify any mistakes you may have made in the implementation. Review the code carefully, debug any issues you find, and provide a corrected version. REMEMBER checking "## WRONG Implementation examples" in the prompt.

3. **Improvement**: Based on the proposed architecture, suggest improvements in the detailed implementation that could increase its performance or effectiveness. In this step, focus on refining and optimizing the existing implementation without altering the overall design framework, except if you want to propose a different architecture if the current is not interesting.
- Observe carefully about whether the implementation is actually doing what it is supposed to do.
- Check if there is redundant code or unnecessary steps in the implementation. Replace them with effective implementation.
- Try to avoid the implementation being too similar to the previous agent.

And then, you need to improve or revise the implementation, or implement the new proposed architecture based on the reflection.

Your response should be organized as follows:

"reflection": Provide your thoughts on the interestingness of the architecture, identify any mistakes in the implementation, and suggest improvements.

"thought": Revise your previous proposal or propose a new architecture if necessary, using the same format as the example response.

"name": Provide a name for the revised or new architecture. (Don't put words like "new" or "improved" in the name.)

"code": Provide the corrected code or an improved implementation. Make sure you actually implement your fix and improvement in this code.
"""

Reflexion_prompt_2 = """Using the tips in "## WRONG Implementation examples" section, revise the code further.
Your response should be organized as follows:
Put your new reflection thinking in "reflection". Repeat the previous "thought" and "name", and update the corrected version of the code in "code".
"""


def get_init_archive():
    # return [COT]#, COT_SC, Reflexion, LLM_debate, Take_a_step_back, QD, Role_Assignment]
    # return [COT_SC]#, COT_SC, Reflexion, LLM_debate, Take_a_step_back, QD, Role_Assignment]
    # return [Reflexion]#, COT_SC, Reflexion, LLM_debate, Take_a_step_back, QD, Role_Assignment]
    # return [COT, COT_SC, Reflexion] # LLM_debate, Take_a_step_back, QD, Role_Assignment]
    return [LLM_debate]


def get_prompt(current_archive, adaptive=False):
    archive_str = ",\n".join([json.dumps(sol) for sol in current_archive])
    archive_str = f"[{archive_str}]"
    prompt = base.replace("[ARCHIVE]", archive_str)
    prompt = prompt.replace("[EXAMPLE]", json.dumps(EXAMPLE))

    return system_prompt, prompt


def get_reflexion_prompt(prev_example):
    prev_example_str = "Here is the previous agent you tried:\n" + json.dumps(prev_example) + "\n\n"
    r1 = Reflexion_prompt_1.replace("[EXAMPLE]", prev_example_str) if prev_example else Reflexion_prompt_1.replace("[EXAMPLE]", "")
    return r1, Reflexion_prompt_2
