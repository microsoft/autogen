from datetime import datetime
from typing import List, Optional

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import MaxMessageTermination, TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat
from autogen_core import ComponentModel
from autogen_core.models import ModelInfo
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from autogen_ext.models.openai import OpenAIChatCompletionClient

from autogenstudio.datamodel import Gallery, GalleryComponents, GalleryItems, GalleryMetadata

from . import tools as tools


class GalleryBuilder:
    """Enhanced builder class for creating AutoGen component galleries with custom labels."""

    def __init__(self, id: str, name: str, url: Optional[str] = None):
        self.id = id
        self.name = name
        self.url: Optional[str] = url
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

    def _update_component_metadata(
        self, component: ComponentModel, label: Optional[str] = None, description: Optional[str] = None
    ) -> ComponentModel:
        """Helper method to update component metadata."""
        if label is not None:
            component.label = label
        if description is not None:
            component.description = description
        return component

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

    def add_team(
        self, team: ComponentModel, label: Optional[str] = None, description: Optional[str] = None
    ) -> "GalleryBuilder":
        """Add a team component to the gallery with optional custom label and description."""
        self.teams.append(self._update_component_metadata(team, label, description))
        return self

    def add_agent(
        self, agent: ComponentModel, label: Optional[str] = None, description: Optional[str] = None
    ) -> "GalleryBuilder":
        """Add an agent component to the gallery with optional custom label and description."""
        self.agents.append(self._update_component_metadata(agent, label, description))
        return self

    def add_model(
        self, model: ComponentModel, label: Optional[str] = None, description: Optional[str] = None
    ) -> "GalleryBuilder":
        """Add a model component to the gallery with optional custom label and description."""
        self.models.append(self._update_component_metadata(model, label, description))
        return self

    def add_tool(
        self, tool: ComponentModel, label: Optional[str] = None, description: Optional[str] = None
    ) -> "GalleryBuilder":
        """Add a tool component to the gallery with optional custom label and description."""
        self.tools.append(self._update_component_metadata(tool, label, description))
        return self

    def add_termination(
        self, termination: ComponentModel, label: Optional[str] = None, description: Optional[str] = None
    ) -> "GalleryBuilder":
        """Add a termination condition component with optional custom label and description."""
        self.terminations.append(self._update_component_metadata(termination, label, description))
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

    # url = "https://raw.githubusercontent.com/microsoft/autogen/refs/heads/main/python/packages/autogen-studio/autogenstudio/gallery/default.json"
    builder = GalleryBuilder(id="gallery_default", name="Default Component Gallery")

    # Set metadata
    builder.set_metadata(
        description="A default gallery containing basic components for human-in-loop conversations",
        tags=["human-in-loop", "assistant", "web agents"],
        category="conversation",
    )

    # Create base model client
    base_model = OpenAIChatCompletionClient(model="gpt-4o-mini")
    builder.add_model(base_model.dump_component())

    # Create Mistral vllm model
    mistral_vllm_model = OpenAIChatCompletionClient(
        model="TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
        base_url="http://localhost:1234/v1",
        model_info=ModelInfo(vision=False, function_calling=True, json_output=False),
    )
    builder.add_model(
        mistral_vllm_model.dump_component(),
        label="Mistral-7B vllm",
        description="Example on how to use the OpenAIChatCopletionClient with local models (Ollama, vllm etc).",
    )

    builder.add_tool(
        tools.calculator_tool.dump_component(),
        label="Calculator Tool",
        description="A tool that performs basic arithmetic operations (addition, subtraction, multiplication, division).",
    )

    # Create calculator assistant agent
    calc_assistant = AssistantAgent(
        name="assistant_agent",
        system_message="You are a helpful assistant. Solve tasks carefully. When done, say TERMINATE.",
        model_client=base_model,
        tools=[tools.calculator_tool],
    )
    builder.add_agent(
        calc_assistant.dump_component(), description="An agent that provides assistance with ability to use tools."
    )

    # Create termination conditions
    calc_text_term = TextMentionTermination(text="TERMINATE")
    calc_max_term = MaxMessageTermination(max_messages=10)
    calc_or_term = calc_text_term | calc_max_term

    builder.add_termination(calc_text_term.dump_component())
    builder.add_termination(calc_max_term.dump_component())
    builder.add_termination(calc_or_term.dump_component())

    # Create calculator team
    calc_team = RoundRobinGroupChat(participants=[calc_assistant], termination_condition=calc_or_term)
    builder.add_team(
        calc_team.dump_component(),
        label="Default Team",
        description="A single AssistantAgent (with a calculator tool) in a RoundRobinGroupChat team. ",
    )

    # Create web surfer agent
    websurfer_agent = MultimodalWebSurfer(
        name="websurfer_agent",
        description="an agent that solves tasks by browsing the web",
        model_client=base_model,
        headless=True,
    )
    builder.add_agent(websurfer_agent.dump_component())

    # Create verification assistant
    verification_assistant = AssistantAgent(
        name="assistant_agent",
        description="an agent that verifies and summarizes information",
        system_message="You are a task verification assistant who is working with a web surfer agent to solve tasks. At each point, check if the task has been completed as requested by the user. If the websurfer_agent responds and the task has not yet been completed, respond with what is left to do and then say 'keep going'. If and only when the task has been completed, summarize and present a final answer that directly addresses the user task in detail and then respond with TERMINATE.",
        model_client=base_model,
    )
    builder.add_agent(verification_assistant.dump_component())

    # Create user proxy
    web_user_proxy = UserProxyAgent(
        name="user_proxy",
        description="a human user that should be consulted only when the assistant_agent is unable to verify the information provided by the websurfer_agent",
    )
    builder.add_agent(web_user_proxy.dump_component())

    # Create web surfer team termination conditions
    web_max_term = MaxMessageTermination(max_messages=20)
    web_text_term = TextMentionTermination(text="TERMINATE")
    web_termination = web_max_term | web_text_term

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
    builder.add_team(
        websurfer_team.dump_component(),
        label="Web Agent Team (Operator)",
        description="A group chat team that have participants takes turn to publish a message\n    to all, using a ChatCompletion model to select the next speaker after each message.",
    )

    builder.add_tool(
        tools.generate_image_tool.dump_component(),
        label="Image Generation Tool",
        description="A tool that generates images based on a text description using OpenAI's DALL-E model. Note: Requires OpenAI API key to function.",
    )

    builder.add_tool(
        tools.generate_pdf_tool.dump_component(),
        label="PDF Generation Tool",
        description="A tool that generates a PDF file from a list of images.Requires the PyFPDF and pillow library to function.",
    )

    builder.add_tool(
        tools.fetch_webpage_tool.dump_component(),
        label="Webpage Generation Tool",
        description="A tool that generates a webpage from a list of images. Requires beautifulsoup4 html2text library to function.",
    )

    builder.add_tool(
        tools.bing_search_tool.dump_component(),
        label="Bing Search Tool",
        description="A tool that performs Bing searches using the Bing Web Search API. Requires the requests library, BING_SEARCH_KEY env variable to function.",
    )

    builder.add_tool(
        tools.google_search_tool.dump_component(),
        label="Google Search Tool",
        description="A tool that performs Google searches using the Google Custom Search API. Requires the requests library, [GOOGLE_API_KEY, GOOGLE_CSE_ID] to be set,  env variable to function.",
    )

    return builder.build()


if __name__ == "__main__":
    # Create and save the gallery
    gallery = create_default_gallery()

    # Save to file
    with open("gallery_default.json", "w") as f:
        f.write(gallery.model_dump_json(indent=2))
