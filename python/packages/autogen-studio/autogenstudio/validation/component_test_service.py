# api/validator/test_service.py
import asyncio
from typing import Any, Dict, List, Optional

from autogen_core import ComponentModel
from autogen_core.models import ChatCompletionClient, UserMessage
from pydantic import BaseModel


class ComponentTestResult(BaseModel):
    status: bool
    message: str
    data: Optional[Any] = None
    logs: List[str] = []


class ComponentTestRequest(BaseModel):
    component: ComponentModel
    model_client: Optional[Dict[str, Any]] = None
    timeout: Optional[int] = 30


class ComponentTestService:
    @staticmethod
    async def test_agent(
        component: ComponentModel, model_client: Optional[ChatCompletionClient] = None
    ) -> ComponentTestResult:
        """Test an agent component with a simple message"""
        try:
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.messages import TextMessage
            from autogen_core import CancellationToken

            # If model_client is provided, use it; otherwise, use the component's model (if applicable)
            agent_config = component.config or {}

            # Try to load the agent
            try:
                # Construct the agent with the model client if provided
                if model_client:
                    agent_config["model_client"] = model_client

                agent = AssistantAgent(name=agent_config.get("name", "assistant"), **agent_config)

                logs = ["Agent component loaded successfully"]
            except Exception as e:
                return ComponentTestResult(
                    status=False,
                    message=f"Failed to initialize agent: {str(e)}",
                    logs=[f"Agent initialization error: {str(e)}"],
                )

            # Test the agent with a simple message
            test_question = "What is 2+2? Keep it brief."
            try:
                response = await agent.on_messages(
                    [TextMessage(content=test_question, source="user")],
                    cancellation_token=CancellationToken(),
                )

                # Check if we got a valid response
                status = response and response.chat_message is not None

                if status:
                    logs.append(
                        f"Agent responded with: {response.chat_message.content} to the question : {test_question}"
                    )
                else:
                    logs.append("Agent did not return a valid response")

                return ComponentTestResult(
                    status=status,
                    message="Agent test completed successfully" if status else "Agent test failed - no valid response",
                    data=response.chat_message.model_dump() if status else None,
                    logs=logs,
                )
            except Exception as e:
                return ComponentTestResult(
                    status=False,
                    message=f"Error during agent response: {str(e)}",
                    logs=logs + [f"Agent response error: {str(e)}"],
                )

        except Exception as e:
            return ComponentTestResult(
                status=False, message=f"Error testing agent component: {str(e)}", logs=[f"Exception: {str(e)}"]
            )

    @staticmethod
    async def test_model(
        component: ComponentModel, model_client: Optional[ChatCompletionClient] = None
    ) -> ComponentTestResult:
        """Test a model component with a simple prompt"""
        try:
            # Use the component itself as a model client
            model = ChatCompletionClient.load_component(component)

            # Prepare a simple test message
            test_question = "What is 2+2? Give me only the answer."
            messages = [UserMessage(content=test_question, source="user")]

            # Try to get a response
            response = await model.create(messages=messages)

            # Test passes if we got a response with content
            status = response and response.content is not None

            logs = ["Model component loaded successfully"]
            if status:
                logs.append(f"Model responded with: {response.content} (Query:{test_question})")
            else:
                logs.append("Model did not return a valid response")

            return ComponentTestResult(
                status=status,
                message="Model test completed successfully" if status else "Model test failed - no valid response",
                data=response.model_dump() if status else None,
                logs=logs,
            )
        except Exception as e:
            return ComponentTestResult(
                status=False, message=f"Error testing model component: {str(e)}", logs=[f"Exception: {str(e)}"]
            )

    @staticmethod
    async def test_tool(component: ComponentModel) -> ComponentTestResult:
        """Test a tool component with sample inputs"""
        # Placeholder for tool test logic
        return ComponentTestResult(
            status=True, message="Tool test not yet implemented", logs=["Tool component loaded successfully"]
        )

    @staticmethod
    async def test_team(
        component: ComponentModel, model_client: Optional[ChatCompletionClient] = None
    ) -> ComponentTestResult:
        """Test a team component with a simple task"""
        # Placeholder for team test logic
        return ComponentTestResult(
            status=True, message="Team test not yet implemented", logs=["Team component loaded successfully"]
        )

    @staticmethod
    async def test_termination(component: ComponentModel) -> ComponentTestResult:
        """Test a termination component with sample message history"""
        # Placeholder for termination test logic
        return ComponentTestResult(
            status=True,
            message="Termination test not yet implemented",
            logs=["Termination component loaded successfully"],
        )

    @classmethod
    async def test_component(
        cls, component: ComponentModel, timeout: int = 60, model_client: Optional[ChatCompletionClient] = None
    ) -> ComponentTestResult:
        """Test a component based on its type with appropriate test inputs"""
        try:
            # Get component type
            component_type = component.component_type

            # Select test method based on component type
            test_method = {
                "agent": cls.test_agent,
                "model": cls.test_model,
                "tool": cls.test_tool,
                "team": cls.test_team,
                "termination": cls.test_termination,
            }.get(component_type or "unknown")

            if not test_method:
                return ComponentTestResult(status=False, message=f"Unknown component type: {component_type}")

            # Determine if the test method accepts a model_client parameter
            accepts_model_client = component_type in ["agent", "model", "team"]

            # Run test with timeout
            try:
                if accepts_model_client:
                    result = await asyncio.wait_for(test_method(component, model_client), timeout=timeout)
                else:
                    result = await asyncio.wait_for(test_method(component), timeout=timeout)
                return result
            except asyncio.TimeoutError:
                return ComponentTestResult(status=False, message=f"Component test exceeded the {timeout}s timeout")

        except Exception as e:
            return ComponentTestResult(status=False, message=f"Error testing component: {str(e)}")
