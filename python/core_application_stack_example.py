"""
AutoGen Core Application Stack Example

Demonstrates the application stack, agent identity, lifecycle, topics, and type-based subscription patterns in AutoGen core.
- Shows how to define message types (behavior contract)
- Implements a code generation workflow with Coder, Executor, and Reviewer agents
- Demonstrates type-based subscription for single-tenant, single-topic scenario

Run: python core_application_stack_example.py
"""
import asyncio
from dataclasses import dataclass
from autogen_core import (
    MessageContext,
    RoutedAgent,
    default_subscription,
    message_handler,
    SingleThreadedAgentRuntime,
    TypeSubscription,
    TopicId,
    AgentId,
)

# Define message types (behavior contract)
@dataclass
class CodingTaskMsg:
    task: str

@dataclass
class CodeGenMsg:
    code: str

@dataclass
class ExecutionResultMsg:
    result: str
    success: bool

@dataclass
class ReviewMsg:
    feedback: str

@dataclass
class CodingResultMsg:
    summary: str

# Agent implementations
@default_subscription
class CoderAgent(RoutedAgent):
    def __init__(self):
        super().__init__("A code generation agent.")

    @message_handler
    async def handle_message(self, message: CodingTaskMsg, ctx: MessageContext) -> None:
        print(f"CoderAgent: Received task: {message.task}")
        code = f"print('Hello from generated code!')  # Task: {message.task}"
        await self.publish_message(CodeGenMsg(code=code), TopicId("execution", "default"))

@default_subscription
class ExecutorAgent(RoutedAgent):
    def __init__(self):
        super().__init__("A code execution agent.")

    @message_handler
    async def handle_message(self, message: CodeGenMsg, ctx: MessageContext) -> None:
        print(f"ExecutorAgent: Executing code: {message.code}")
        # Simulate execution
        result = "Execution successful! Output: Hello from generated code!"
        await self.publish_message(ExecutionResultMsg(result=result, success=True), TopicId("review", "default"))

@default_subscription
class ReviewerAgent(RoutedAgent):
    def __init__(self):
        super().__init__("A code review agent.")

    @message_handler
    async def handle_message(self, message: ExecutionResultMsg, ctx: MessageContext) -> None:
        print(f"ReviewerAgent: Reviewing execution result: {message.result}")
        if message.success:
            summary = "Code executed successfully. Review passed."
        else:
            summary = "Code execution failed. Needs revision."
        await self.publish_message(CodingResultMsg(summary=summary), TopicId("result", "default"))

async def main() -> None:
    runtime = SingleThreadedAgentRuntime()
    # Register type-based subscriptions for single-tenant, single-topic
    runtime.add_type_subscription(TypeSubscription("task", "coder_agent"))
    runtime.add_type_subscription(TypeSubscription("execution", "executor_agent"))
    runtime.add_type_subscription(TypeSubscription("review", "reviewer_agent"))
    # Register agent types
    await CoderAgent.register(runtime, "coder_agent", lambda: CoderAgent())
    await ExecutorAgent.register(runtime, "executor_agent", lambda: ExecutorAgent())
    await ReviewerAgent.register(runtime, "reviewer_agent", lambda: ReviewerAgent())
    # Start runtime and publish a coding task
    runtime.start()
    await runtime.publish_message(CodingTaskMsg(task="Generate a hello world script."), TopicId("task", "default"))
    await runtime.stop_when_idle()

if __name__ == "__main__":
    asyncio.run(main())
