"""
Example usage of ApprovalGuard with CodeExecutorAgent and MagenticOne

This example demonstrates how to use the new ApprovalGuard functionality
integrated into CodeExecutorAgent and MagenticOne team.
"""

import asyncio
from autogen_agentchat.agents import CodeExecutorAgent
from autogen_agentchat.approval_guard import ApprovalGuard, ApprovalConfig
from autogen_agentchat.messages import TextMessage
from autogen_core import CancellationToken
from autogen_ext.code_executors.docker import DockerCommandLineCodeExecutor
from autogen_ext.teams.magentic_one import MagenticOne
from autogen_ext.models.openai import OpenAIChatCompletionClient


async def simple_input_func(prompt: str, cancellation_token=None):
    """Simple input function for demonstration."""
    print(f"\n=== APPROVAL REQUEST ===")
    print(prompt)
    print("========================")
    # In a real implementation, this would get user input
    # For this example, we'll auto-approve safe actions
    if "print" in prompt.lower() and "hello" in prompt.lower():
        return "yes"
    else:
        return "no"


async def example_code_executor_with_approval():
    """Example: CodeExecutorAgent with ApprovalGuard"""
    
    print("=== CodeExecutorAgent with ApprovalGuard Example ===\n")
    
    # Create an approval guard with always policy
    approval_guard = ApprovalGuard(
        input_func=simple_input_func,
        config=ApprovalConfig(approval_policy="always")
    )
    
    # Create CodeExecutorAgent with approval guard
    code_executor = DockerCommandLineCodeExecutor()
    await code_executor.start()
    
    agent = CodeExecutorAgent(
        name="code_executor_with_approval",
        code_executor=code_executor,
        approval_guard=approval_guard
    )
    
    # Test with safe code
    safe_message = TextMessage(
        content='''
```python
print("Hello, World!")
```
''',
        source="user"
    )
    
    print("Sending safe code execution request...")
    try:
        response = await agent.on_messages([safe_message], CancellationToken())
        print(f"Response: {response.chat_message.content}")
    except Exception as e:
        print(f"Error: {e}")
    
    await code_executor.stop()


async def example_magentic_one_with_approval():
    """Example: MagenticOne with ApprovalGuard"""
    
    print("\n=== MagenticOne with ApprovalGuard Example ===\n")
    
    # Create OpenAI client (you would need a real API key)
    # client = OpenAIChatCompletionClient(model="gpt-4o", api_key="your-key")
    
    # Create approval guard with conservative policy
    approval_guard = ApprovalGuard(
        input_func=simple_input_func,
        config=ApprovalConfig(approval_policy="auto-conservative")
    )
    
    # Create MagenticOne team with approval guard
    # team = MagenticOne(client=client, approval_guard=approval_guard)
    
    print("MagenticOne team would be created with approval guard.")
    print("Code execution through the team would require approval.")


async def example_approval_policies():
    """Example: Different approval policies"""
    
    print("\n=== Different Approval Policies Example ===\n")
    
    policies = ["always", "never", "auto-conservative", "auto-permissive"]
    
    for policy in policies:
        print(f"Policy: {policy}")
        guard = ApprovalGuard(
            config=ApprovalConfig(approval_policy=policy),
            default_approval=False
        )
        
        requires_approval = await guard.requires_approval(
            baseline="maybe",
            llm_guess="maybe",
            action_context=[]
        )
        
        print(f"  Requires approval: {requires_approval}\n")


if __name__ == "__main__":
    # Note: These examples show the API usage
    # Full execution would require proper setup and API keys
    
    print("ApprovalGuard Integration Examples")
    print("=" * 50)
    
    # Run policy examples (these work without dependencies)
    asyncio.run(example_approval_policies())
    
    # Other examples would require full setup
    print("Note: CodeExecutorAgent and MagenticOne examples require")
    print("proper environment setup and API keys to run fully.")
    
    print("\nAPI Usage Summary:")
    print("1. Create ApprovalGuard with desired policy")
    print("2. Pass approval_guard to CodeExecutorAgent constructor")
    print("3. Pass approval_guard to MagenticOne constructor")
    print("4. Code execution will request approval based on policy")