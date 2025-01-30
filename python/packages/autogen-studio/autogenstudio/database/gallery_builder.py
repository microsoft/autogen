from datetime import datetime
from typing import List, Optional

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat
from autogen_core import ComponentModel
from autogen_core.models import ModelInfo
from autogen_core.tools import FunctionTool
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from autogen_ext.models.openai import OpenAIChatCompletionClient

from autogenstudio.datamodel import Gallery, GalleryComponents, GalleryItems, GalleryMetadata


class GalleryBuilder:
    """Builder class for creating AutoGen component galleries."""

    def __init__(self, id: str, name: str):
        self.id = id
        self.name = name
        self.url: Optional[str] = None
        self.teams: List[ComponentModel] = []
        self.agents: List[ComponentModel] = []
        self.models: List[ComponentModel] = []
        self.tools: List[ComponentModel] = []
        self.terminations: List[ComponentModel] = []

        # Default metadata
        self.metadata = GalleryMetadata(
            author="AutoGen Team",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            version="1.0.0",
            description="",
            tags=[],
            license="MIT",
            category="conversation",
        )

    def set_metadata(
        self,
        author: Optional[str] = None,
        version: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        license: Optional[str] = None,
        category: Optional[str] = None,
    ) -> "GalleryBuilder":
        """Update gallery metadata."""
        if author:
            self.metadata.author = author
        if version:
            self.metadata.version = version
        if description:
            self.metadata.description = description
        if tags:
            self.metadata.tags = tags
        if license:
            self.metadata.license = license
        if category:
            self.metadata.category = category
        return self

    def add_team(self, team: ComponentModel) -> "GalleryBuilder":
        """Add a team component to the gallery."""
        self.teams.append(team)
        return self

    def add_agent(self, agent: ComponentModel) -> "GalleryBuilder":
        """Add an agent component to the gallery."""
        self.agents.append(agent)
        return self

    def add_model(self, model: ComponentModel) -> "GalleryBuilder":
        """Add a model component to the gallery."""
        self.models.append(model)
        return self

    def add_tool(self, tool: ComponentModel) -> "GalleryBuilder":
        """Add a tool component to the gallery."""
        self.tools.append(tool)
        return self

    def add_termination(self, termination: ComponentModel) -> "GalleryBuilder":
        """Add a termination condition component to the gallery."""
        self.terminations.append(termination)
        return self

    def build(self) -> Gallery:
        """Build and return the complete gallery."""
        # Update timestamps
        self.metadata.updated_at = datetime.now()

        return Gallery(
            id=self.id,
            name=self.name,
            url=self.url,
            metadata=self.metadata,
            items=GalleryItems(
                teams=self.teams,
                components=GalleryComponents(
                    agents=self.agents, models=self.models, tools=self.tools, terminations=self.terminations
                ),
            ),
        )


def create_default_gallery() -> Gallery:
    """Create a default gallery with all components including calculator and web surfer teams."""
    builder = GalleryBuilder(id="gallery_default", name="Default Component Gallery")

    # Set metadata
    builder.set_metadata(
        description="A default gallery containing basic components for human-in-loop conversations",
        tags=["human-in-loop", "assistant"],
        category="conversation",
    )

    # Create base model client
    base_model = OpenAIChatCompletionClient(model="gpt-4o-mini")
    builder.add_model(base_model.dump_component())

    mistral_vllm_model = OpenAIChatCompletionClient(
        model="TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
        base_url="http://localhost:1234/v1",
        model_info=ModelInfo(vision=False, function_calling=True, json_output=False),
    )
    builder.add_model(mistral_vllm_model.dump_component())

    # Create websurfer model client
    websurfer_model = OpenAIChatCompletionClient(model="gpt-4o-mini")
    builder.add_model(websurfer_model.dump_component())

    def calculator(a: float, b: float, operator: str) -> str:
        try:
            if operator == "+":
                return str(a + b)
            elif operator == "-":
                return str(a - b)
            elif operator == "*":
                return str(a * b)
            elif operator == "/":
                if b == 0:
                    return "Error: Division by zero"
                return str(a / b)
            else:
                return "Error: Invalid operator. Please use +, -, *, or /"
        except Exception as e:
            return f"Error: {str(e)}"

    # Create calculator tool
    calculator_tool = FunctionTool(
        name="calculator",
        description="A simple calculator that performs basic arithmetic operations",
        func=calculator,
        global_imports=[],
    )
    builder.add_tool(calculator_tool.dump_component())

    # Create termination conditions for calculator team
    calc_text_term = TextMentionTermination(text="TERMINATE")
    calc_max_term = MaxMessageTermination(max_messages=10)
    calc_or_term = calc_text_term | calc_max_term

    builder.add_termination(calc_text_term.dump_component())
    builder.add_termination(calc_max_term.dump_component())
    builder.add_termination(calc_or_term.dump_component())

    # Create calculator assistant agent
    calc_assistant = AssistantAgent(
        name="assistant_agent",
        system_message="You are a helpful assistant. Solve tasks carefully. When done, say TERMINATE.",
        model_client=base_model,
        tools=[calculator_tool],
    )
    builder.add_agent(calc_assistant.dump_component())

    # Create calculator team
    calc_team = RoundRobinGroupChat(participants=[calc_assistant], termination_condition=calc_or_term)
    builder.add_team(calc_team.dump_component())

    # Create web surfer agent
    websurfer_agent = MultimodalWebSurfer(
        name="websurfer_agent",
        description="an agent that solves tasks by browsing the web",
        model_client=websurfer_model,
        headless=True,
    )
    builder.add_agent(websurfer_agent.dump_component())

    # Create web surfer verification assistant
    verification_assistant = AssistantAgent(
        name="assistant_agent",
        description="an agent that verifies and summarizes information",
        system_message="You are a task verification assistant who is working with a web surfer agent to solve tasks. At each point, check if the task has been completed as requested by the user. If the websurfer_agent responds and the task has not yet been completed, respond with what is left to do and then say 'keep going'. If and only when the task has been completed, summarize and present a final answer that directly addresses the user task in detail and then respond with TERMINATE.",
        model_client=websurfer_model,
    )
    builder.add_agent(verification_assistant.dump_component())

    # Create web surfer user proxy
    web_user_proxy = UserProxyAgent(
        name="user_proxy",
        description="a human user that should be consulted only when the assistant_agent is unable to verify the information provided by the websurfer_agent",
    )
    builder.add_agent(web_user_proxy.dump_component())

    # Create web surfer team termination conditions
    web_max_term = MaxMessageTermination(max_messages=20)
    web_text_term = TextMentionTermination(text="TERMINATE")
    web_termination = web_max_term | web_text_term
    builder.add_termination(web_termination.dump_component())

    # Create web surfer team
    selector_prompt = """You are the cordinator of role play game. The following roles are available:
{roles}. Given a task, the websurfer_agent will be tasked to address it by browsing the web and providing information.  The assistant_agent will be tasked with verifying the information provided by the websurfer_agent and summarizing the information to present a final answer to the user. If the task  needs assistance from a human user (e.g., providing feedback, preferences, or the task is stalled), you should select the user_proxy role to provide the necessary information.
Read the following conversation. Then select the next role from {participants} to play. Only return the role.

{history}

Read the above conversation. Then select the next role from {participants} to play. Only return the role."""

    websurfer_team = SelectorGroupChat(
        participants=[websurfer_agent, verification_assistant, web_user_proxy],
        selector_prompt=selector_prompt,
        model_client=base_model,
        termination_condition=web_termination,
    )
    builder.add_team(websurfer_team.dump_component())

    return builder.build()


# if __name__ == "__main__":
#     # Create and save the gallery
#     gallery = create_default_gallery()

#     # Print as JSON
#     print(gallery.model_dump_json(indent=2))

#     # Save to file
#     with open("gallery_default.json", "w") as f:
#         f.write(gallery.model_dump_json(indent=2))
