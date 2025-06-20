#!/usr/bin/env python3
"""
Example demonstrating the AutoGen Agent Optimizer interface.

This example shows how to use the optimization interface, including:
1. Creating an agent with tools
2. Preparing a training dataset
3. Using the compile() function to optimize the agent
4. Checking available backends

Note: This example requires DSPy to be installed for actual optimization.
Run: pip install dspy
"""

import asyncio
from unittest.mock import Mock

def main():
    """Demonstrate the AutoGen Agent Optimizer interface."""
    print("=== AutoGen Agent Optimizer Demo ===\n")
    
    # Import the optimization interface
    from autogen_agentchat.optimize import compile, list_backends
    
    # Import DSPy backend to register it (safe import)
    try:
        from autogen_ext.optimize import dspy  # This will register the backend
    except ImportError:
        pass  # DSPy backend not available
    
    print("1. Available optimization backends:")
    backends = list_backends()
    print(f"   {backends}")
    print()
    
    # ➊ Build a toy agent ---------------------------------------------------
    print("2. Creating a simple agent with tools...")
    
    class SimpleAgent:
        """Mock agent for demonstration."""
        def __init__(self, name: str, system_message: str):
            self.name = name
            self.system_message = system_message
            self._system_messages = []
            if system_message:
                # Mock SystemMessage class
                class SystemMessage:
                    def __init__(self, content):
                        self.content = content
                self._system_messages = [SystemMessage(system_message)]
            
            # Mock tools
            self._tools = []
            self.model_client = Mock()  # Mock model client
            
        def add_tool(self, name: str, description: str):
            """Add a mock tool to the agent."""
            class MockTool:
                def __init__(self, name, description):
                    self.name = name
                    self.description = description
            
            self._tools.append(MockTool(name, description))
    
    # Create the agent
    agent = SimpleAgent(
        name="calc",
        system_message="You are a helpful calculator assistant."
    )
    
    # Add a tool
    agent.add_tool("add", "Add two numbers together")
    
    print(f"   Agent: {agent.name}")
    print(f"   System message: {agent.system_message}")
    print(f"   Tools: {[(t.name, t.description) for t in agent._tools]}")
    print()
    
    # ➋ Minimal trainset  ----------------------------------------------------
    print("3. Creating training dataset...")
    
    # Mock DSPy Example format
    class MockExample:
        def __init__(self, user_request: str, answer: str):
            self.user_request = user_request
            self.answer = answer
            
        def with_inputs(self, *inputs):
            return self
    
    train = [
        MockExample(user_request="2+2", answer="4").with_inputs("user_request"),
        MockExample(user_request="Add 3 and 5", answer="8").with_inputs("user_request"),
    ]
    
    print(f"   Training examples: {len(train)}")
    for i, ex in enumerate(train):
        print(f"   Example {i+1}: '{ex.user_request}' -> '{ex.answer}'")
    print()
    
    # ➌ Define metric --------------------------------------------------------
    print("4. Defining evaluation metric...")
    
    def metric(gold, pred, **kwargs):
        """Simple exact match metric."""
        return getattr(gold, 'answer', gold) == getattr(pred, 'answer', pred)
    
    print("   Using exact match metric")
    print()
    
    # ➍ Optimize using the unified API --------------------------------------
    print("5. Attempting optimization...")
    
    try:
        # This is the main interface as specified in the issue
        opt_agent, report = compile(
            agent=agent,
            trainset=train,
            metric=metric,
            backend="dspy",                    # default anyway
            optimizer_name="MIPROv2",
            optimizer_kwargs=dict(max_steps=8),
        )
        
        print("✓ Optimization completed successfully!")
        print("\nOptimization Report:")
        for key, value in report.items():
            print(f"   {key}: {value}")
            
        print(f"\nOptimized agent system message:")
        print(f"   {opt_agent.system_message}")
        
    except ImportError as e:
        print(f"⚠ DSPy not available: {e}")
        print("\nTo run actual optimization, install DSPy:")
        print("   pip install dspy")
        print("\nThe interface is ready to use once DSPy is installed!")
        
    except Exception as e:
        print(f"❌ Optimization failed: {e}")
    
    print("\n=== Demo Complete ===")


if __name__ == "__main__":
    main()