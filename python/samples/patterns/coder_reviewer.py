"""
This example shows how to use publish-subscribe to implement
a simple interaction between a coder and a reviewer agent.
1. The coder agent receives a code writing task message, generates a code block,
and publishes a code review task message.
2. The reviewer agent receives the code review task message, reviews the code block,
and publishes a code review result message.
3. The coder agent receives the code review result message, depending on the result:
if the code is approved, it publishes a code writing result message; otherwise, it generates
a new code block and publishes a code review task message.
4. The process continues until the coder agent publishes a code writing result message.
"""

import asyncio
import json
import os
import re
import sys
import uuid
from dataclasses import dataclass
from typing import Dict, List, Union

from agnext.application import SingleThreadedAgentRuntime
from agnext.components import TypeRoutedAgent, message_handler
from agnext.components._type_subscription import TypeSubscription
from agnext.components.models import (
    AssistantMessage,
    ChatCompletionClient,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from agnext.core import TopicId

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agnext.core import MessageContext
from common.utils import get_chat_completion_client_from_envs


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
    session_id: str
    code_writing_task: str
    code_writing_scratchpad: str
    code: str


@dataclass
class CodeReviewResult:
    review: str
    session_id: str
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
    async def handle_code_review_task(self, message: CodeReviewTask, ctx: MessageContext) -> None:
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
            self._system_messages + [UserMessage(content=prompt, source=self.metadata["type"])]
        )
        assert isinstance(response.content, str)
        # TODO: use structured generation library e.g. guidance to ensure the response is in the expected format.
        # Parse the response JSON.
        review = json.loads(response.content)
        # Construct the review text.
        review_text = "Code review:\n" + "\n".join([f"{k}: {v}" for k, v in review.items()])
        approved = review["approval"].lower().strip() == "approve"
        # Publish the review result.
        assert ctx.topic_id is not None
        await self.publish_message(
            CodeReviewResult(
                review=review_text,
                approved=approved,
                session_id=message.session_id,
            ),
            topic_id=ctx.topic_id,
        )


class CoderAgent(TypeRoutedAgent):
    """An agent that performs code writing tasks."""

    def __init__(
        self,
        description: str,
        model_client: ChatCompletionClient,
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
        self._session_memory: Dict[str, List[CodeWritingTask | CodeReviewTask | CodeReviewResult]] = {}

    @message_handler
    async def handle_code_writing_task(
        self,
        message: CodeWritingTask,
        ctx: MessageContext,
    ) -> None:
        # Store the messages in a temporary memory for this request only.
        session_id = str(uuid.uuid4())
        self._session_memory.setdefault(session_id, []).append(message)
        # Generate a response using the chat completion API.
        response = await self._model_client.create(
            self._system_messages + [UserMessage(content=message.task, source=self.metadata["type"])]
        )
        assert isinstance(response.content, str)
        # Extract the code block from the response.
        code_block = self._extract_code_block(response.content)
        if code_block is None:
            raise ValueError("Code block not found.")
        # Create a code review task.
        code_review_task = CodeReviewTask(
            session_id=session_id,
            code_writing_task=message.task,
            code_writing_scratchpad=response.content,
            code=code_block,
        )
        # Store the code review task in the session memory.
        self._session_memory[session_id].append(code_review_task)
        # Publish a code review task.
        assert ctx.topic_id is not None
        await self.publish_message(
            code_review_task,
            topic_id=ctx.topic_id,
        )

    @message_handler
    async def handle_code_review_result(self, message: CodeReviewResult, ctx: MessageContext) -> None:
        # Store the review result in the session memory.
        self._session_memory[message.session_id].append(message)
        # Obtain the request from previous messages.
        review_request = next(
            m for m in reversed(self._session_memory[message.session_id]) if isinstance(m, CodeReviewTask)
        )
        assert review_request is not None
        # Check if the code is approved.
        if message.approved:
            # Publish the code writing result.
            assert ctx.topic_id is not None
            await self.publish_message(
                CodeWritingResult(
                    code=review_request.code,
                    task=review_request.code_writing_task,
                    review=message.review,
                ),
                topic_id=ctx.topic_id,
            )
            print("Code Writing Result:")
            print("-" * 80)
            print(f"Task:\n{review_request.code_writing_task}")
            print("-" * 80)
            print(f"Code:\n{review_request.code}")
            print("-" * 80)
            print(f"Review:\n{message.review}")
            print("-" * 80)
        else:
            # Create a list of LLM messages to send to the model.
            messages: List[LLMMessage] = [*self._system_messages]
            for m in self._session_memory[message.session_id]:
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
            # Create a new code review task.
            code_review_task = CodeReviewTask(
                session_id=message.session_id,
                code_writing_task=review_request.code_writing_task,
                code_writing_scratchpad=response.content,
                code=code_block,
            )
            # Store the code review task in the session memory.
            self._session_memory[message.session_id].append(code_review_task)
            # Publish a new code review task.
            assert ctx.topic_id is not None
            await self.publish_message(
                code_review_task,
                topic_id=ctx.topic_id,
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
    await runtime.register(
        "ReviewerAgent",
        lambda: ReviewerAgent(
            description="Code Reviewer",
            model_client=get_chat_completion_client_from_envs(model="gpt-4o-mini"),
        ),
    )
    await runtime.add_subscription(TypeSubscription("default", "ReviewerAgent"))
    await runtime.register(
        "CoderAgent",
        lambda: CoderAgent(
            description="Coder",
            model_client=get_chat_completion_client_from_envs(model="gpt-4o-mini"),
        ),
    )
    await runtime.add_subscription(TypeSubscription("default", "CoderAgent"))
    runtime.start()
    await runtime.publish_message(
        message=CodeWritingTask(
            task="Write a function to find the directory with the largest number of files using multi-processing."
        ),
        topic_id=TopicId("default", "default"),
    )

    # Keep processing messages until idle.
    await runtime.stop_when_idle()


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("agnext").setLevel(logging.DEBUG)
    asyncio.run(main())
