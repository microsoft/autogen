#!/usr/bin/env python3
"""
GPT-5 Agent Integration Examples for AutoGen

This script demonstrates how to integrate GPT-5's advanced features
with AutoGen agents and multi-agent systems:

1. GPT-5 powered AssistantAgent with reasoning control
2. Multi-agent systems with GPT-5 optimization
3. Specialized agents for different GPT-5 capabilities
4. Agent conversation with chain-of-thought preservation
5. Tool-specialized agents with custom GPT-5 tools

This showcases enterprise-grade patterns for GPT-5 integration.
"""

import asyncio
import os
from typing import Any, Dict, List

from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import SelectorGroupChat
from autogen_core import CancellationToken
from autogen_core.models import UserMessage
from autogen_core.tools import BaseCustomTool, CustomToolFormat
from autogen_ext.models.openai import OpenAIChatCompletionClient, OpenAIResponsesAPIClient


class DataAnalysisTool(BaseCustomTool[str]):
    """GPT-5 custom tool for data analysis with freeform input."""
    
    def __init__(self):
        super().__init__(
            return_type=str,
            name="data_analysis",
            description="Analyze data and generate insights. Input should be data description or analysis request.",
        )
    
    async def run(self, input_text: str, cancellation_token: CancellationToken) -> str:
        """Simulate data analysis."""
        # In production, this would connect to data analysis tools
        analysis_types = {
            "trend": "📈 Trend analysis shows upward trajectory with seasonal variations",
            "correlation": "🔗 Strong positive correlation (r=0.85) detected between variables",
            "outlier": "⚠️ 3 outliers detected requiring attention",
            "summary": "📊 Dataset summary: 1000 records, normal distribution, complete data"
        }
        
        analysis_type = "summary"  # Default
        for key in analysis_types:
            if key in input_text.lower():
                analysis_type = key
                break
                
        return f"Data Analysis Results:\n{analysis_types[analysis_type]}\n\nDetailed analysis: {input_text}"


class ResearchTool(BaseCustomTool[str]):
    """GPT-5 custom tool for research tasks."""
    
    def __init__(self):
        super().__init__(
            return_type=str,
            name="research",
            description="Conduct research and gather information on specified topics.",
        )
    
    async def run(self, input_text: str, cancellation_token: CancellationToken) -> str:
        """Simulate research functionality."""
        return f"🔍 Research Results for: {input_text}\n" \
               f"• Found 15 relevant academic papers\n" \
               f"• Identified 3 key trends\n" \
               f"• Generated comprehensive summary with citations\n" \
               f"• Confidence level: High"


class CodeReviewTool(BaseCustomTool[str]):
    """GPT-5 custom tool with grammar constraints for code review."""
    
    def __init__(self):
        # Define grammar for code review requests
        code_review_grammar = CustomToolFormat(
            type="grammar",
            syntax="lark", 
            definition="""
                start: review_request
                
                review_request: "REVIEW" language_spec code_block review_type?
                
                language_spec: "LANG:" IDENTIFIER
                
                code_block: "CODE:" code_content
                
                code_content: /[\\s\\S]+/
                
                review_type: "TYPE:" review_focus
                
                review_focus: "security" | "performance" | "style" | "bugs" | "all"
                
                IDENTIFIER: /[a-zA-Z_][a-zA-Z0-9_+#-]*/
                
                %import common.WS
                %ignore WS
            """
        )
        
        super().__init__(
            return_type=str,
            name="code_review",
            description="Review code with structured input. Format: REVIEW LANG:python CODE:your_code TYPE:security",
            format=code_review_grammar,
        )
    
    async def run(self, input_text: str, cancellation_token: CancellationToken) -> str:
        """Perform structured code review."""
        return f"📝 Code Review Complete:\n" \
               f"Input: {input_text}\n" \
               f"✅ No security vulnerabilities found\n" \
               f"⚡ Performance suggestions: Use list comprehension\n" \
               f"🎨 Style: Follows PEP 8 guidelines\n" \
               f"🐛 No bugs detected\n" \
               f"Overall: Production ready"


class GPT5ReasoningAgent:
    """Assistant agent optimized for GPT-5 reasoning tasks."""
    
    def __init__(self, name: str, reasoning_effort: str = "high"):
        self.name = name
        self.client = OpenAIChatCompletionClient(
            model="gpt-5",
            api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here")
        )
        self.reasoning_effort = reasoning_effort
        
        # Configure for reasoning tasks
        self.system_message = """
        You are a reasoning specialist powered by GPT-5. Your role is to:
        1. Break down complex problems into manageable parts
        2. Apply systematic thinking and analysis
        3. Provide clear explanations of your reasoning process
        4. Verify conclusions and consider alternative perspectives
        
        Use your advanced reasoning capabilities to provide thoughtful, well-structured responses.
        """
    
    async def process_request(self, user_input: str) -> str:
        """Process user request with optimized reasoning."""
        response = await self.client.create(
            messages=[
                UserMessage(content=self.system_message, source="system"),
                UserMessage(content=user_input, source="user")
            ],
            reasoning_effort=self.reasoning_effort,
            verbosity="high",  # Detailed explanations
            preambles=True
        )
        
        return response.content


class GPT5CodeAgent:
    """Assistant agent optimized for GPT-5 code generation tasks."""
    
    def __init__(self, name: str):
        self.name = name
        self.client = OpenAIChatCompletionClient(
            model="gpt-5",
            api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here")
        )
        
        # Initialize code-related tools
        self.code_review_tool = CodeReviewTool()
        
        self.system_message = """
        You are a code generation specialist powered by GPT-5. Your role is to:
        1. Generate high-quality, production-ready code
        2. Follow best practices and coding standards
        3. Provide clear documentation and comments
        4. Consider security, performance, and maintainability
        
        Use your advanced capabilities to write excellent code.
        """
    
    async def process_request(self, user_input: str) -> str:
        """Process code-related requests."""
        response = await self.client.create(
            messages=[
                UserMessage(content=self.system_message, source="system"),
                UserMessage(content=user_input, source="user")
            ],
            tools=[self.code_review_tool],
            reasoning_effort="low",  # Code tasks need less reasoning
            verbosity="medium",
            preambles=True  # Explain code choices
        )
        
        return response.content


class GPT5AnalysisAgent:
    """Assistant agent optimized for data analysis with GPT-5."""
    
    def __init__(self, name: str):
        self.name = name
        self.client = OpenAIChatCompletionClient(
            model="gpt-5-mini",  # Cost-effective for analysis tasks
            api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here")
        )
        
        # Initialize analysis tools
        self.data_tool = DataAnalysisTool()
        self.research_tool = ResearchTool()
        
        self.system_message = """
        You are a data analysis specialist powered by GPT-5. Your role is to:
        1. Analyze data patterns and trends
        2. Generate actionable insights
        3. Create clear visualizations and reports
        4. Provide evidence-based recommendations
        
        Use your analytical capabilities to uncover valuable insights.
        """
    
    async def process_request(self, user_input: str) -> str:
        """Process analysis requests."""
        response = await self.client.create(
            messages=[
                UserMessage(content=self.system_message, source="system"),
                UserMessage(content=user_input, source="user")
            ],
            tools=[self.data_tool, self.research_tool],
            reasoning_effort="medium",
            verbosity="high",  # Detailed analysis reports
            preambles=True
        )
        
        return response.content


class GPT5ConversationManager:
    """Manages multi-turn conversations with chain-of-thought preservation."""
    
    def __init__(self):
        self.client = OpenAIResponsesAPIClient(
            model="gpt-5",
            api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here")
        )
        self.conversation_history = []
        self.last_response_id = None
    
    async def continue_conversation(self, user_input: str, reasoning_effort: str = "medium") -> Dict[str, Any]:
        """Continue conversation with CoT preservation."""
        response = await self.client.create(
            input=user_input,
            previous_response_id=self.last_response_id,
            reasoning_effort=reasoning_effort,
            verbosity="medium",
            preambles=True
        )
        
        # Update conversation state
        self.conversation_history.append({
            "user_input": user_input,
            "response": response.content,
            "reasoning": response.thought,
            "response_id": getattr(response, 'response_id', None)
        })
        
        self.last_response_id = getattr(response, 'response_id', None)
        
        return {
            "content": response.content,
            "reasoning": response.thought,
            "usage": response.usage,
            "turn_number": len(self.conversation_history)
        }


async def demonstrate_gpt5_reasoning_agent():
    """Demonstrate specialized reasoning agent."""
    
    print("🧠 GPT-5 Reasoning Agent Example")
    print("=" * 50)
    
    reasoning_agent = GPT5ReasoningAgent("ReasoningSpecialist", reasoning_effort="high")
    
    complex_problem = """
    A company has three departments: Engineering (50 people), Sales (30 people), and Marketing (20 people).
    They want to form cross-functional teams of 5 people each, with at least one person from each department.
    What's the maximum number of teams they can form, and how should they distribute people?
    """
    
    print("Complex Problem:")
    print(complex_problem)
    print("\nReasoning Agent Response:")
    
    response = await reasoning_agent.process_request(complex_problem)
    print(response)
    
    await reasoning_agent.client.close()


async def demonstrate_gpt5_code_agent():
    """Demonstrate specialized code generation agent."""
    
    print("\n💻 GPT-5 Code Agent Example")
    print("=" * 50)
    
    code_agent = GPT5CodeAgent("CodeSpecialist")
    
    code_request = """
    Create a Python class for a thread-safe LRU cache with the following requirements:
    1. Maximum capacity that can be set at initialization
    2. get() and put() methods
    3. Thread safety using locks
    4. O(1) average time complexity for both operations
    5. Proper error handling
    """
    
    print("Code Request:")
    print(code_request)
    print("\nCode Agent Response:")
    
    response = await code_agent.process_request(code_request)
    print(response)
    
    await code_agent.client.close()


async def demonstrate_gpt5_analysis_agent():
    """Demonstrate data analysis agent with custom tools."""
    
    print("\n📊 GPT-5 Analysis Agent Example")
    print("=" * 50)
    
    analysis_agent = GPT5AnalysisAgent("AnalysisSpecialist")
    
    analysis_request = """
    I have sales data showing monthly revenue for the past 2 years.
    The data shows seasonal patterns with peaks in Q4 and dips in Q1.
    Can you analyze this trend data and provide insights for business planning?
    """
    
    print("Analysis Request:")
    print(analysis_request)
    print("\nAnalysis Agent Response:")
    
    response = await analysis_agent.process_request(analysis_request)
    print(response)
    
    await analysis_agent.client.close()


async def demonstrate_multi_turn_conversation():
    """Demonstrate multi-turn conversation with CoT preservation."""
    
    print("\n💬 GPT-5 Multi-Turn Conversation Example")
    print("=" * 50)
    
    conversation_manager = GPT5ConversationManager()
    
    # Turn 1: Initial complex question
    print("\nTurn 1: Initial Architecture Question")
    response1 = await conversation_manager.continue_conversation(
        "Design a microservices architecture for an e-commerce platform that needs to handle 1 million daily active users",
        reasoning_effort="high"
    )
    
    print(f"Response: {response1['content'][:300]}...")
    print(f"Turn: {response1['turn_number']}, Tokens: {response1['usage'].total_tokens}")
    
    # Turn 2: Follow-up with context preservation
    print("\nTurn 2: Follow-up on Database Strategy")
    response2 = await conversation_manager.continue_conversation(
        "How would you handle database sharding and data consistency in this architecture?",
        reasoning_effort="medium"  # Lower effort due to preserved context
    )
    
    print(f"Response: {response2['content'][:300]}...")
    print(f"Turn: {response2['turn_number']}, Tokens: {response2['usage'].total_tokens}")
    
    # Turn 3: Implementation details
    print("\nTurn 3: Implementation Details")
    response3 = await conversation_manager.continue_conversation(
        "Show me the API design for the user service with authentication",
        reasoning_effort="low"  # Minimal reasoning needed with established context
    )
    
    print(f"Response: {response3['content'][:300]}...")
    print(f"Turn: {response3['turn_number']}, Tokens: {response3['usage'].total_tokens}")
    
    print(f"\nTotal conversation turns: {len(conversation_manager.conversation_history)}")
    
    await conversation_manager.client.close()


async def demonstrate_agent_collaboration():
    """Demonstrate multiple GPT-5 agents working together."""
    
    print("\n🤝 GPT-5 Multi-Agent Collaboration Example") 
    print("=" * 50)
    
    # Initialize specialized agents
    reasoning_agent = GPT5ReasoningAgent("Strategist", reasoning_effort="high")
    code_agent = GPT5CodeAgent("Developer")
    analysis_agent = GPT5AnalysisAgent("Analyst")
    
    project_brief = """
    Project: Build a real-time analytics dashboard for monitoring website performance
    Requirements: Track page load times, user engagement, error rates, and conversion metrics
    Constraints: Must handle 10K concurrent users, sub-second query response times
    """
    
    print("Project Brief:")
    print(project_brief)
    
    # Agent 1: Strategic analysis
    print("\n🧠 Strategist (Reasoning Agent):")
    strategy_response = await reasoning_agent.process_request(
        f"Analyze this project and provide a strategic approach:\n{project_brief}"
    )
    print(strategy_response[:400] + "...")
    
    # Agent 2: Technical implementation
    print("\n💻 Developer (Code Agent):")
    code_response = await code_agent.process_request(
        f"Based on the strategy, design the technical architecture and provide code examples for the analytics dashboard"
    )
    print(code_response[:400] + "...")
    
    # Agent 3: Performance analysis
    print("\n📊 Analyst (Analysis Agent):")
    analysis_response = await analysis_agent.process_request(
        f"Analyze the performance requirements and suggest optimization strategies for the dashboard"
    )
    print(analysis_response[:400] + "...")
    
    print("\n✅ Multi-agent collaboration complete!")
    
    # Cleanup
    await reasoning_agent.client.close()
    await code_agent.client.close() 
    await analysis_agent.client.close()


async def demonstrate_tool_specialization():
    """Demonstrate agents with different tool specializations."""
    
    print("\n🛠️ GPT-5 Tool Specialization Example")
    print("=" * 50)
    
    # Create an agent that restricts tool usage for safety
    client = OpenAIChatCompletionClient(
        model="gpt-5",
        api_key=os.getenv("OPENAI_API_KEY", "your-api-key-here")
    )
    
    # All available tools
    data_tool = DataAnalysisTool()
    research_tool = ResearchTool()
    code_review_tool = CodeReviewTool()
    
    all_tools = [data_tool, research_tool, code_review_tool]
    safe_tools = [data_tool, research_tool]  # Exclude code review for this task
    
    print("Tool Specialization: Data-focused agent (restricted tools)")
    
    response = await client.create(
        messages=[UserMessage(
            content="I need help analyzing user engagement data and researching industry benchmarks, but I also want code review",
            source="user"
        )],
        tools=all_tools,
        allowed_tools=safe_tools,  # Restrict to safe tools only
        tool_choice="auto",
        reasoning_effort="medium",
        verbosity="medium",
        preambles=True  # Explain tool restrictions
    )
    
    print(f"Agent Response: {response.content}")
    if response.thought:
        print(f"Tool Usage Explanation: {response.thought}")
    
    await client.close()


async def main():
    """Run all GPT-5 agent integration examples."""
    
    print("🚀 GPT-5 Agent Integration Demo")
    print("=" * 60)
    print("Showcasing enterprise-grade GPT-5 integration with AutoGen agents")
    print("")
    
    try:
        # Run all agent examples
        await demonstrate_gpt5_reasoning_agent()
        await demonstrate_gpt5_code_agent()
        await demonstrate_gpt5_analysis_agent()
        await demonstrate_multi_turn_conversation()
        await demonstrate_agent_collaboration()
        await demonstrate_tool_specialization()
        
        print("\n🎉 All GPT-5 agent integration examples completed!")
        print("=" * 60)
        print("Enterprise Integration Patterns Demonstrated:")
        print("• Specialized agents for different GPT-5 capabilities")
        print("• Multi-turn conversations with chain-of-thought preservation")
        print("• Multi-agent collaboration with GPT-5 optimization")
        print("• Tool specialization and access control")
        print("• Cost optimization using appropriate model variants")
        
    except Exception as e:
        print(f"\n❌ Error running agent examples: {e}")
        print("Ensure your OPENAI_API_KEY is set and you have GPT-5 access")


if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Warning: OPENAI_API_KEY environment variable not found.")
        print("Please set it with: export OPENAI_API_KEY='your-api-key-here'")
    
    asyncio.run(main())