#!/usr/bin/env python3
"""
GPT-5 Basic Usage Examples for AutoGen

This script demonstrates the key features and usage patterns of GPT-5
with AutoGen, including:

1. Basic GPT-5 model usage with reasoning control
2. Custom tools with freeform text input
3. Grammar-constrained custom tools  
4. Multi-turn conversations with chain-of-thought preservation
5. Tool restrictions with allowed_tools parameter
6. Responses API for optimized performance

Run this script to see GPT-5 features in action.
"""

import asyncio
import os
from typing import Literal

from autogen_core import CancellationToken
from autogen_core.models import UserMessage
from autogen_core.tools import BaseCustomTool, CustomToolFormat
from autogen_ext.models.openai import OpenAIChatCompletionClient, OpenAIResponsesAPIClient
from pydantic import BaseModel
import json


class TextResult(BaseModel):
    text: str


def _coerce_content_to_text(content: object) -> str:
    if isinstance(content, str):
        return content
    try:
        return json.dumps(content, ensure_ascii=False, default=str)
    except Exception:
        return str(content)


ReasoningEffort = Literal["minimal", "low", "medium", "high"]


class CodeExecutorTool(BaseCustomTool[TextResult]):
    """GPT-5 custom tool for executing Python code with freeform text input."""
    
    def __init__(self):
        super().__init__(
            return_type=TextResult,
            name="code_exec",
            description="Executes Python code and returns the output. Input should be valid Python code.",
        )
    
    async def run(self, input_text: str, cancellation_token: CancellationToken) -> TextResult:
        """Execute Python code safely (in a real implementation, use proper sandboxing)."""
        try:
            # In production, use proper sandboxing like RestrictedPython or containers
            # This is a simplified example
            import io
            from contextlib import redirect_stdout
            
            output = io.StringIO()
            with redirect_stdout(output):
                exec(
                    input_text,
                    {
                        "__builtins__": {
                            "print": print,
                            "len": len,
                            "str": str,
                            "int": int,
                            "float": float,
                        }
                    },
                )
            
            result = output.getvalue()
            text = (
                f"Code executed successfully:\n{result}" if result else "Code executed successfully (no output)"
            )
            return TextResult(text=text)
            
        except Exception as e:  # noqa: BLE001
            return TextResult(text=f"Error executing code: {e}")


class SQLQueryTool(BaseCustomTool[TextResult]):
    """GPT-5 custom tool with grammar constraints for SQL queries."""
    
    def __init__(self):
        # Define SQL grammar using Lark syntax
        sql_grammar = CustomToolFormat(
            type="grammar",
            syntax="lark",
            definition=r"""
                start: select_statement
                
                select_statement: "SELECT" column_list "FROM" table_name where_clause?
                
                column_list: column ("," column)*
                           | "*"
                
                column: IDENTIFIER
                
                table_name: IDENTIFIER
                
                where_clause: "WHERE" condition
                
                condition: column operator value
                
                operator: "=" | ">" | "<" | ">=" | "<=" | "!="
                
                value: NUMBER | STRING
                
                IDENTIFIER: /[a-zA-Z_][a-zA-Z0-9_]*/
                NUMBER: /[0-9]+(\.[0-9]+)?/
                STRING: /"[^"]*"/
                
                %import common.WS
                %ignore WS
            """,
        )
        
        super().__init__(
            return_type=TextResult,
            name="sql_query",
            description="Execute SQL SELECT queries with grammar validation. Only SELECT statements are allowed.",
            format=sql_grammar,
        )
    
    async def run(self, input_text: str, cancellation_token: CancellationToken) -> TextResult:
        """Simulate SQL query execution."""
        # In a real implementation, this would connect to a database
        # This is a mock response for demonstration
        return TextResult(
            text=(
                f"SQL Query Results:\nExecuted: {input_text}\nResult: [Mock data returned - 3 rows affected]"
            )
        )


class CalculatorTool(BaseCustomTool[TextResult]):
    """Simple calculator tool for safe mathematical operations."""
    
    def __init__(self):
        super().__init__(
            return_type=TextResult,
            name="calculator",
            description=(
                "Perform basic mathematical calculations safely. Input should be a mathematical expression."
            ),
        )
    
    async def run(self, input_text: str, cancellation_token: CancellationToken) -> TextResult:
        """Safely evaluate mathematical expressions."""
        try:
            import ast
            import operator
            
            allowed_ops: dict[type[ast.AST], object] = {
                ast.Add: operator.add,
                ast.Sub: operator.sub,
                ast.Mult: operator.mul,
                ast.Div: operator.truediv,
                ast.Mod: operator.mod,
                ast.Pow: operator.pow,
                ast.USub: operator.neg,
            }
            
            def safe_eval(node: ast.AST) -> float | int:
                if isinstance(node, ast.Expression):
                    return safe_eval(node.body)  # type: ignore[arg-type]
                if isinstance(node, ast.Constant):
                    if isinstance(node.value, (int, float)):
                        return node.value
                    raise ValueError("Only numeric constants are allowed")
                if isinstance(node, ast.BinOp):
                    left = safe_eval(node.left)
                    right = safe_eval(node.right)
                    op = allowed_ops.get(type(node.op))
                    if op:
                        return op(left, right)  # type: ignore[call-arg]
                if isinstance(node, ast.UnaryOp):
                    operand = safe_eval(node.operand)
                    op = allowed_ops.get(type(node.op))
                    if op:
                        return op(operand)  # type: ignore[call-arg]
                raise ValueError(f"Unsupported operation: {type(node)}")
            
            tree = ast.parse(input_text, mode="eval")
            result = safe_eval(tree)
            return TextResult(text=f"Calculation result: {result}")
            
        except Exception as e:  # noqa: BLE001
            return TextResult(text=f"Error in calculation: {e}")


async def demonstrate_gpt5_basic_usage():
    """Demonstrate basic GPT-5 usage with reasoning control."""
    
    print("🚀 GPT-5 Basic Usage Example")
    print("=" * 50)
    
    # Initialize GPT-5 client
    client = OpenAIChatCompletionClient(
        model="gpt-5",
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here"),
    )
    
    # Example 1: Basic reasoning with different effort levels
    print("\n1. Reasoning Effort Control:")
    print("-" * 30)
    
    # High reasoning for complex problems
    response = await client.create(
        messages=[UserMessage(
            content="Explain the concept of quantum entanglement and its implications for quantum computing",
            source="user",
        )],
        reasoning_effort="high",
        verbosity="medium",
        preambles=True,
    )
    
    print(f"High reasoning response: {_coerce_content_to_text(response.content)}")
    if response.thought:
        print(f"Reasoning process: {response.thought}")
    
    # Minimal reasoning for simple tasks
    response = await client.create(
        messages=[UserMessage(
            content="What's 2 + 2?",
            source="user",
        )],
        reasoning_effort="minimal",
        verbosity="low",
    )
    
    print(f"Minimal reasoning response: {_coerce_content_to_text(response.content)}")
    
    await client.close()


async def demonstrate_gpt5_custom_tools():
    """Demonstrate GPT-5 custom tools with freeform text input."""
    
    print("\n🛠️ GPT-5 Custom Tools Example")
    print("=" * 50)
    
    client = OpenAIChatCompletionClient(
        model="gpt-5",
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here"),
    )
    
    # Initialize custom tools
    code_tool = CodeExecutorTool()
    sql_tool = SQLQueryTool()
    
    print("\n2. Custom Tool with Freeform Input:")
    print("-" * 40)
    
    # Code execution example
    response = await client.create(
        messages=[UserMessage(
            content="Calculate the factorial of 8 using Python code",
            source="user",
        )],
        tools=[code_tool],
        reasoning_effort="medium",
        verbosity="low",
        preambles=True,  # Explain why tools are used
    )
    
    print(f"Tool response: {_coerce_content_to_text(response.content)}")
    if response.thought:
        print(f"Tool explanation: {response.thought}")
    
    print("\n3. Grammar-Constrained Custom Tool:")
    print("-" * 40)
    
    # SQL query with grammar constraints
    response = await client.create(
        messages=[UserMessage(
            content="Query all users from the users table where age is greater than 25",
            source="user",
        )],
        tools=[sql_tool],
        reasoning_effort="low",
        preambles=True,
    )
    
    print(f"SQL response: {_coerce_content_to_text(response.content)}")
    
    await client.close()


async def demonstrate_allowed_tools():
    """Demonstrate allowed_tools parameter for restricting model behavior."""
    
    print("\n🔒 GPT-5 Allowed Tools Example")
    print("=" * 50)
    
    client = OpenAIChatCompletionClient(
        model="gpt-5",
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here"),
    )
    
    # Create multiple tools
    code_tool = CodeExecutorTool()
    sql_tool = SQLQueryTool()
    calc_tool = CalculatorTool()
    
    all_tools = [code_tool, sql_tool, calc_tool]
    safe_tools = [calc_tool]  # Only allow calculator for safety
    
    print("\n4. Restricted Tool Access:")
    print("-" * 30)
    
    response = await client.create(
        messages=[UserMessage(
            content="I need help with calculations, database queries, and code execution",
            source="user",
        )],
        tools=all_tools,
        allowed_tools=safe_tools,  # Restrict to only calculator
        tool_choice="auto",
        reasoning_effort="medium",
        preambles=True,
    )
    
    print(f"Restricted response: {_coerce_content_to_text(response.content)}")
    if response.thought:
        print(f"Tool restriction explanation: {response.thought}")
    
    await client.close()


async def demonstrate_responses_api():
    """Demonstrate GPT-5 Responses API for optimized multi-turn conversations."""
    
    print("\n💬 GPT-5 Responses API Example")
    print("=" * 50)
    
    # Use the Responses API for better performance in multi-turn conversations
    client = OpenAIResponsesAPIClient(
        model="gpt-5",
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here"),
    )
    
    print("\n5. Multi-Turn Conversation with CoT Preservation:")
    print("-" * 50)
    
    # Turn 1: Initial complex question requiring high reasoning
    print("Turn 1: Complex initial question")
    response1 = await client.create(
        input="Design a distributed system architecture for a real-time chat application that can handle millions of users",
        reasoning_effort="high",
        verbosity="medium",
        preambles=True,
    )
    
    print(f"Response 1: {_coerce_content_to_text(response1.content)}")
    if response1.thought:
        print(f"Reasoning 1: {response1.thought[:200]}...")
    
    # Turn 2: Follow-up question with preserved context
    print("\nTurn 2: Follow-up with preserved reasoning context")
    response2 = await client.create(
        input="How would you handle data consistency in this distributed system?",
        previous_response_id=getattr(response1, 'response_id', None),  # Preserve CoT context
        reasoning_effort="medium",  # Can use lower effort due to context
        verbosity="medium",
    )
    
    print(f"Response 2: {_coerce_content_to_text(response2.content)}")
    
    # Turn 3: Implementation request with tools
    print("\nTurn 3: Implementation with custom tools")
    code_tool = CodeExecutorTool()
    
    response3 = await client.create(
        input="Show me a simple example of the message routing logic in Python",
        previous_response_id=getattr(response2, 'response_id', None),
        tools=[code_tool],
        reasoning_effort="low",  # Minimal reasoning needed due to established context
        preambles=True,
    )
    
    print(f"Response 3: {_coerce_content_to_text(response3.content)}")
    if response3.thought:
        print(f"Implementation explanation: {response3.thought}")
    
    await client.close()


async def demonstrate_model_variants():
    """Demonstrate different GPT-5 model variants."""
    
    print("\n🎯 GPT-5 Model Variants Example")
    print("=" * 50)
    
    print("\n6. Model Variant Comparison:")
    print("-" * 30)
    
    # GPT-5 (full model)
    gpt5_client = OpenAIChatCompletionClient(
        model="gpt-5",
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here"),
    )
    
    # GPT-5 Mini (cost-optimized)
    gpt5_mini_client = OpenAIChatCompletionClient(
        model="gpt-5-mini", 
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here"),
    )
    
    # GPT-5 Nano (high-throughput)
    gpt5_nano_client = OpenAIChatCompletionClient(
        model="gpt-5-nano",
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here"),
    )
    
    question = "Briefly explain machine learning"
    
    # Compare responses from different variants
    print("GPT-5 (full model):")
    response = await gpt5_client.create(
        messages=[UserMessage(content=question, source="user")],
        reasoning_effort="medium",
        verbosity="medium",
    )
    print(f"  {_coerce_content_to_text(response.content)[:100]}...")
    print(f"  Token usage: {response.usage.prompt_tokens + response.usage.completion_tokens}")
    
    print("\nGPT-5 Mini (cost-optimized):")
    response = await gpt5_mini_client.create(
        messages=[UserMessage(content=question, source="user")],
        reasoning_effort="medium",
        verbosity="medium",
    )
    print(f"  {_coerce_content_to_text(response.content)[:100]}...")
    print(f"  Token usage: {response.usage.prompt_tokens + response.usage.completion_tokens}")
    
    print("\nGPT-5 Nano (high-throughput):")
    response = await gpt5_nano_client.create(
        messages=[UserMessage(content=question, source="user")],
        reasoning_effort="minimal",
        verbosity="low",
    )
    print(f"  {_coerce_content_to_text(response.content)[:100]}...")
    print(f"  Token usage: {response.usage.prompt_tokens + response.usage.completion_tokens}")
    
    await gpt5_client.close()
    await gpt5_mini_client.close()
    await gpt5_nano_client.close()


async def main():
    """Run all GPT-5 examples."""
    
    print("🎉 Welcome to GPT-5 Features Demo with AutoGen!")
    print("=" * 60)
    print("This demo showcases the key GPT-5 features and capabilities.")
    print("Make sure to set your OPENAI_API_KEY environment variable.")
    print("")
    
    try:
        # Run all examples
        await demonstrate_gpt5_basic_usage()
        await demonstrate_gpt5_custom_tools()
        await demonstrate_allowed_tools()
        await demonstrate_responses_api()
        await demonstrate_model_variants()
        
        print("\n🎊 All GPT-5 examples completed successfully!")
        print("=" * 60)
        print("Key takeaways:")
        print("• GPT-5 offers fine-grained reasoning and verbosity control")
        print("• Custom tools accept freeform text input with optional grammar constraints")
        print("• Allowed tools parameter provides safety through tool restrictions")
        print("• Responses API optimizes multi-turn conversations with CoT preservation")
        print("• Different model variants (gpt-5, gpt-5-mini, gpt-5-nano) balance performance and cost")
        
    except Exception as e:  # noqa: BLE001
        print(f"\n❌ Error running examples: {e}")
        print("Make sure you have:")
        print("1. Set OPENAI_API_KEY environment variable")
        print("2. Installed required dependencies: pip install autogen-ext[openai]")
        print("3. Have access to GPT-5 models in your OpenAI account")


if __name__ == "__main__":
    # Set up example API key if not in environment
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Warning: OPENAI_API_KEY environment variable not found.")
        print("Please set it with: export OPENAI_API_KEY='your-api-key-here'")
        print("Or uncomment the line below to set it in code (not recommended for production)")
        # os.environ["OPENAI_API_KEY"] = "your-api-key-here"
    
    asyncio.run(main())