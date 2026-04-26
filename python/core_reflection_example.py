"""
Reflection Design Pattern Example (Coder/Reviewer Agents)

This example demonstrates the Reflection pattern using AutoGen agents. A coder agent generates code for a given task, and a reviewer agent critiques the code. The process iterates until the reviewer approves the code or a stopping condition is met.

Requirements:
- autogen-core, autogen-ext (install in editable mode)
- OpenAI API key (set OPENAI_API_KEY)

Run with: python python/core_reflection_example.py
"""
import asyncio
import json
import re
import uuid
from dataclasses import dataclass
from typing import Dict, List, Union

from autogen_core import (
    DefaultTopicId,
    MessageContext,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    TopicId,
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

# ------------------- Coder Agent -------------------
@default_subscription
class CoderAgent(RoutedAgent):
    """An agent that performs code writing tasks."""
    def __init__(self, model_client: ChatCompletionClient) -> None:
        super().__init__("A code writing agent.")
        self._system_messages: List[LLMMessage] = [
            SystemMessage(
                content="""You are a proficient coder. You write code to solve problems.\nWork with the reviewer to improve your code.\nAlways put all finished code in a single Markdown code block.\nFor example:\n```python\ndef hello_world():\n    print(\"Hello, World!\")\n```\n\nRespond using the following format:\n\nThoughts: <Your comments>\nCode: <Your code>\n""",
            )
        ]
        self._model_client = model_client
        self._session_memory: Dict[str, List[CodeWritingTask | CodeReviewTask | CodeReviewResult]] = {}

    @message_handler
    async def handle_code_writing_task(self, message: CodeWritingTask, ctx: MessageContext) -> None:
        session_id = str(uuid.uuid4())
        self._session_memory.setdefault(session_id, []).append(message)
        response = await self._model_client.create(
            self._system_messages + [UserMessage(content=message.task, source=self.metadata["type"])],
            cancellation_token=ctx.cancellation_token,
        )
        assert isinstance(response.content, str)
        code_block = self._extract_code_block(response.content)
        if code_block is None:
            raise ValueError("Code block not found.")
        code_review_task = CodeReviewTask(
            session_id=session_id,
            code_writing_task=message.task,
            code_writing_scratchpad=response.content,
            code=code_block,
        )
        self._session_memory[session_id].append(code_review_task)
        await self.publish_message(code_review_task, topic_id=TopicId("default", self.id.key))

    @message_handler
    async def handle_code_review_result(self, message: CodeReviewResult, ctx: MessageContext) -> None:
        self._session_memory[message.session_id].append(message)
        review_request = next(
            m for m in reversed(self._session_memory[message.session_id]) if isinstance(m, CodeReviewTask)
        )
        assert review_request is not None
        if message.approved:
            await self.publish_message(
                CodeWritingResult(
                    code=review_request.code,
                    task=review_request.code_writing_task,
                    review=message.review,
                ),
                topic_id=TopicId("default", self.id.key),
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
            response = await self._model_client.create(messages, cancellation_token=ctx.cancellation_token)
            assert isinstance(response.content, str)
            code_block = self._extract_code_block(response.content)
            if code_block is None:
                raise ValueError("Code block not found.")
            code_review_task = CodeReviewTask(
                session_id=message.session_id,
                code_writing_task=review_request.code_writing_task,
                code_writing_scratchpad=response.content,
                code=code_block,
            )
            self._session_memory[message.session_id].append(code_review_task)
            await self.publish_message(code_review_task, topic_id=TopicId("default", self.id.key))

    def _extract_code_block(self, markdown_text: str) -> Union[str, None]:
        pattern = r"```(\w+)\n(.*?)\n```"
        match = re.search(pattern, markdown_text, re.DOTALL)
        if match:
            return match.group(2)
        return None

# ------------------- Reviewer Agent -------------------
@default_subscription
class ReviewerAgent(RoutedAgent):
    """An agent that performs code review tasks."""
    def __init__(self, model_client: ChatCompletionClient) -> None:
        super().__init__("A code reviewer agent.")
        self._system_messages: List[LLMMessage] = [
            SystemMessage(
                content="""You are a code reviewer. You focus on correctness, efficiency and safety of the code.\nRespond using the following JSON format:\n{\n    \"correctness\": \"<Your comments>\",\n    \"efficiency\": \"<Your comments>\",\n    \"safety\": \"<Your comments>\",\n    \"approval\": \"APPROVE or REVISE\",\n    \"suggested_changes\": \"<Your comments>\"\n}\n""",
            )
        ]
        self._session_memory: Dict[str, List[CodeReviewTask | CodeReviewResult]] = {}
        self._model_client = model_client

    @message_handler
    async def handle_code_review_task(self, message: CodeReviewTask, ctx: MessageContext) -> None:
        previous_feedback = ""
        if message.session_id in self._session_memory:
            previous_review = next(
                (m for m in reversed(self._session_memory[message.session_id]) if isinstance(m, CodeReviewResult)),
                None,
            )
            if previous_review is not None:
                previous_feedback = previous_review.review
        self._session_memory.setdefault(message.session_id, []).append(message)
        prompt = f"""The problem statement is: {message.code_writing_task}\nThe code is:\n```
{message.code}
```
\nPrevious feedback:\n{previous_feedback}\n\nPlease review the code. If previous feedback was provided, see if it was addressed.\n"""
        response = await self._model_client.create(
            self._system_messages + [UserMessage(content=prompt, source=self.metadata["type"])],
            cancellation_token=ctx.cancellation_token,
            json_output=True,
        )
        assert isinstance(response.content, str)
        review = json.loads(response.content)
        review_text = "Code review:\n" + "\n".join([f"{k}: {v}" for k, v in review.items()])
        approved = review["approval"].lower().strip() == "approve"
        result = CodeReviewResult(
            review=review_text,
            session_id=message.session_id,
            approved=approved,
        )
        self._session_memory[message.session_id].append(result)
        await self.publish_message(result, topic_id=TopicId("default", self.id.key))

# ------------------- Main Reflection Setup -------------------
async def main():
    import logging
    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("autogen_core").setLevel(logging.DEBUG)

    runtime = SingleThreadedAgentRuntime()
    model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")
    await ReviewerAgent.register(runtime, "ReviewerAgent", lambda: ReviewerAgent(model_client=model_client))
    await CoderAgent.register(runtime, "CoderAgent", lambda: CoderAgent(model_client=model_client))
    runtime.start()
    await runtime.publish_message(
        message=CodeWritingTask(task="Write a function to find the sum of all even numbers in a list."),
        topic_id=DefaultTopicId(),
    )
    await runtime.stop_when_idle()
    await model_client.close()

if __name__ == "__main__":
    asyncio.run(main())
