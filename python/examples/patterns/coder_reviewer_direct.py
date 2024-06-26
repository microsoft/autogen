"""
This example shows how to use direct messaging to implement
a simple interaction between a coder and a reviewer agent.
1. The coder agent receives a code writing task message, generates a code block,
and sends a code review task message to the reviewer agent.
2. The reviewer agent receives the code review task message, reviews the code block,
and sends a code review result message to the coder agent.
3. The coder agent receives the code review result message, depending on the result:
if the code is approved, it sends a code writing result message; otherwise, it generates
a new code block and sends a code review task message.
4. The process continues until the coder agent receives an approved code review result message.
5. The main function prints the code writing result.
"""

import asyncio
import json
import re
from dataclasses import dataclass
from typing import List, Union

from agnext.application import SingleThreadedAgentRuntime
from agnext.components import TypeRoutedAgent, message_handler
from agnext.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    LLMMessage,
    OpenAIChatCompletionClient,
    SystemMessage,
    UserMessage,
)
from agnext.core import AgentId, CancellationToken


@dataclass
class CodeWritingTask:
    task: str


@dataclass
class CodeWritingResult:
    task: str
    code: str
    review: str


@dataclass
class CodeReviewTask:
    code_writing_task: str
    code_writing_scratchpad: str
    code: str


@dataclass
class CodeReviewResult:
    review: str
    approved: bool


class ReviewerAgent(TypeRoutedAgent):
    """An agent that performs code review tasks."""

    def __init__(
        self,
        description: str,
        model_client: ChatCompletionClient,
    ) -> None:
        super().__init__(description)
        self._system_messages = [
            SystemMessage(
                content="""You are a code reviewer. You focus on correctness, efficiency and safety of the code.
Respond using the following JSON format:
{
    "correctness": "<Your comments>",
    "efficiency": "<Your comments>",
    "safety": "<Your comments>",
    "approval": "<APPROVE or REVISE>",
    "suggested_changes": "<Your comments>"
}
""",
            )
        ]
        self._model_client = model_client

    @message_handler
    async def handle_code_review_task(
        self, message: CodeReviewTask, cancellation_token: CancellationToken
    ) -> CodeReviewResult:
        # Format the prompt for the code review.
        prompt = f"""The problem statement is: {message.code_writing_task}
The code is:
```
{message.code}
```
Please review the code and provide feedback.
"""
        # Generate a response using the chat completion API.
        response = await self._model_client.create(
            self._system_messages + [UserMessage(content=prompt, source=self.metadata["name"])]
        )
        assert isinstance(response.content, str)
        # TODO: use structured generation library e.g. guidance to ensure the response is in the expected format.
        # Parse the response JSON.
        review = json.loads(response.content)
        # Construct the review text.
        review_text = "Code review:\n" + "\n".join([f"{k}: {v}" for k, v in review.items()])
        approved = review["approval"].lower().strip() == "approve"
        # Return the review result.
        return CodeReviewResult(
            review=review_text,
            approved=approved,
        )


class CoderAgent(TypeRoutedAgent):
    """An agent that performs code writing tasks."""

    def __init__(
        self,
        description: str,
        model_client: ChatCompletionClient,
        reviewer: AgentId,
    ) -> None:
        super().__init__(
            description,
        )
        self._system_messages = [
            SystemMessage(
                content="""You are a proficient coder. You write code to solve problems.
Work with the reviewer to improve your code.
Always put all finished code in a single Markdown code block.
For example:
```python
def hello_world():
    print("Hello, World!")
```

Respond using the following format:

Thoughts: <Your comments>
Code: <Your code>
""",
            )
        ]
        self._model_client = model_client
        self._reviewer = reviewer

    @message_handler
    async def handle_code_writing_task(
        self,
        message: CodeWritingTask,
        cancellation_token: CancellationToken,
    ) -> CodeWritingResult:
        # Store the messages in a temporary memory for this request only.
        memory: List[CodeWritingTask | CodeReviewTask | CodeReviewResult] = []
        memory.append(message)
        # Keep generating responses until the code is approved.
        while not (isinstance(memory[-1], CodeReviewResult) and memory[-1].approved):
            # Create a list of LLM messages to send to the model.
            messages: List[LLMMessage] = [*self._system_messages]
            for m in memory:
                if isinstance(m, CodeReviewResult):
                    messages.append(UserMessage(content=m.review, source="Reviewer"))
                elif isinstance(m, CodeReviewTask):
                    messages.append(AssistantMessage(content=m.code_writing_scratchpad, source="Coder"))
                elif isinstance(m, CodeWritingTask):
                    messages.append(UserMessage(content=m.task, source="User"))
                else:
                    raise ValueError(f"Unexpected message type: {m}")
            # Generate a revision using the chat completion API.
            response = await self._model_client.create(messages)
            assert isinstance(response.content, str)
            # Extract the code block from the response.
            code_block = self._extract_code_block(response.content)
            if code_block is None:
                raise ValueError("Code block not found.")
            # Create a code review task.
            code_review_task = CodeReviewTask(
                code_writing_task=message.task,
                code_writing_scratchpad=response.content,
                code=code_block,
            )
            # Store the code review task in the session memory.
            memory.append(code_review_task)
            # Send the code review task to the reviewer.
            result = await self.send_message(code_review_task, self._reviewer)
            # Store the review result in the session memory.
            memory.append(result)
        # Obtain the request from previous messages.
        review_request = next(m for m in reversed(memory) if isinstance(m, CodeReviewTask))
        assert review_request is not None
        # Publish the code writing result.
        return CodeWritingResult(
            task=message.task,
            code=review_request.code,
            review=memory[-1].review,
        )

    def _extract_code_block(self, markdown_text: str) -> Union[str, None]:
        pattern = r"```(\w+)\n(.*?)\n```"
        # Search for the pattern in the markdown text
        match = re.search(pattern, markdown_text, re.DOTALL)
        # Extract the language and code block if a match is found
        if match:
            return match.group(2)
        return None


async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    reviewer = runtime.register_and_get(
        "ReviewerAgent",
        lambda: ReviewerAgent(
            description="Code Reviewer",
            model_client=OpenAIChatCompletionClient(model="gpt-3.5-turbo"),
        ),
    )
    coder = runtime.register_and_get(
        "CoderAgent",
        lambda: CoderAgent(
            description="Coder",
            model_client=OpenAIChatCompletionClient(model="gpt-3.5-turbo"),
            reviewer=reviewer,
        ),
    )
    result = runtime.send_message(
        message=CodeWritingTask(
            task="Write a function to find the directory with the largest number of files using multi-processing."
        ),
        recipient=coder,
    )
    while not result.done():
        await runtime.process_next()
    code_writing_result = result.result()
    assert isinstance(code_writing_result, CodeWritingResult)
    print("Code Writing Result:")
    print("-" * 80)
    print(f"Task:\n{code_writing_result.task}")
    print("-" * 80)
    print(f"Code:\n{code_writing_result.code}")
    print("-" * 80)
    print(f"Review:\n{code_writing_result.review}")


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("agnext").setLevel(logging.DEBUG)
    asyncio.run(main())
