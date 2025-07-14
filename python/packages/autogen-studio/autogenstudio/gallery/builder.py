import os
from typing import List, Optional

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import (
    HandoffTermination,
    MaxMessageTermination,
    SourceMatchTermination,
    StopMessageTermination,
    TextMentionTermination,
    TextMessageTermination,
    TimeoutTermination,
    TokenUsageTermination,
)
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat, Swarm
from autogen_core import ComponentModel
from autogen_core.models import ModelInfo
from autogen_core.tools import StaticWorkbench
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.models.anthropic import AnthropicChatCompletionClient
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.models.openai._openai_client import AzureOpenAIChatCompletionClient
from autogen_ext.tools.code_execution import PythonCodeExecutionTool
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams, StreamableHttpServerParams

from autogenstudio.datamodel import GalleryComponents, GalleryConfig, GalleryMetadata

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
        self.workbenches: List[ComponentModel] = []

        # Default metadata
        self.metadata = GalleryMetadata(
            author="AutoGen Team",
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

    def add_workbench(
        self, workbench: ComponentModel, label: Optional[str] = None, description: Optional[str] = None
    ) -> "GalleryBuilder":
        """Add a workbench component to the gallery with optional custom label and description."""
        self.workbenches.append(self._update_component_metadata(workbench, label, description))
        return self

    def build(self) -> GalleryConfig:
        """Build and return the complete gallery."""
        # Update timestamps
        # self.metadata.updated_at = datetime.now()

        return GalleryConfig(
            id=self.id,
            name=self.name,
            url=self.url,
            metadata=self.metadata,
            components=GalleryComponents(
                teams=self.teams,
                agents=self.agents,
                models=self.models,
                tools=self.tools,
                terminations=self.terminations,
                workbenches=self.workbenches,
            ),
        )


def create_default_gallery() -> GalleryConfig:
    """Create a default gallery with all components including calculator and web surfer teams."""

    # model clients require API keys to be set in the environment or passed in
    # as arguments. For testing purposes, we set them to "test" if not already set.
    for key in ["OPENAI_API_KEY", "AZURE_OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
        if not os.environ.get(key):
            os.environ[key] = "test"

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
    builder.add_model(base_model.dump_component(), label="OpenAI GPT-4o Mini", description="OpenAI GPT-4o-mini")
    # Create Mistral vllm model
    mistral_vllm_model = OpenAIChatCompletionClient(
        model="TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
        base_url="http://localhost:1234/v1",
        model_info=ModelInfo(
            vision=False, function_calling=True, json_output=False, family="unknown", structured_output=False
        ),
    )
    builder.add_model(
        mistral_vllm_model.dump_component(),
        label="Mistral-7B Local",
        description="Local Mistral-7B model client for instruction-based generation (Ollama, LMStudio).",
    )

    anthropic_model = AnthropicChatCompletionClient(model="claude-3-7-sonnet-20250219")
    builder.add_model(
        anthropic_model.dump_component(),
        label="Anthropic Claude-3-7",
        description="Anthropic Claude-3 model client.",
    )

    # create an azure mode
    az_model_client = AzureOpenAIChatCompletionClient(
        azure_deployment="{your-azure-deployment}",
        model="gpt-4o-mini",
        api_version="2024-06-01",
        azure_endpoint="https://{your-custom-endpoint}.openai.azure.com/",
        api_key="test",
    )
    builder.add_model(
        az_model_client.dump_component(),
        label="AzureOpenAI GPT-4o-mini",
        description="GPT-4o Mini Azure OpenAI model client.",
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
    builder.add_termination(
        calc_or_term.dump_component(),
        label="OR Termination",
        description="Termination condition that ends the conversation when either a message contains 'TERMINATE' or the maximum number of messages is reached.",
    )

    # Add examples of new termination conditions

    # StopMessageTermination - terminates when a StopMessage is received
    stop_msg_term = StopMessageTermination()
    builder.add_termination(
        stop_msg_term.dump_component(),
        label="Stop Message Termination",
        description="Terminates the conversation when a StopMessage is received from any agent.",
    )

    # TokenUsageTermination - terminates based on token usage limits
    token_usage_term = TokenUsageTermination(max_total_token=1000, max_prompt_token=800, max_completion_token=200)
    builder.add_termination(
        token_usage_term.dump_component(),
        label="Token Usage Termination",
        description="Terminates the conversation when token usage limits are reached (1000 total, 800 prompt, 200 completion).",
    )

    # TimeoutTermination - terminates after a specified duration
    timeout_term = TimeoutTermination(timeout_seconds=300)  # 5 minutes
    builder.add_termination(
        timeout_term.dump_component(),
        label="Timeout Termination",
        description="Terminates the conversation after 5 minutes (300 seconds) have elapsed.",
    )

    # HandoffTermination - terminates when handoff to specific target occurs
    handoff_term = HandoffTermination(target="user_proxy")
    builder.add_termination(
        handoff_term.dump_component(),
        label="Handoff Termination",
        description="Terminates the conversation when a handoff to 'user_proxy' is detected.",
    )

    # SourceMatchTermination - terminates when specific sources respond
    source_match_term = SourceMatchTermination(sources=["assistant_agent", "critic_agent"])
    builder.add_termination(
        source_match_term.dump_component(),
        label="Source Match Termination",
        description="Terminates the conversation when either 'assistant_agent' or 'critic_agent' responds.",
    )

    # TextMessageTermination - terminates on TextMessage from specific source
    text_msg_term = TextMessageTermination(source="assistant_agent")
    builder.add_termination(
        text_msg_term.dump_component(),
        label="Text Message Termination",
        description="Terminates the conversation when a TextMessage is received from 'assistant_agent'.",
    )

    # Create a complex termination combining multiple conditions
    complex_term = (token_usage_term | timeout_term) & (calc_text_term | stop_msg_term)
    builder.add_termination(
        complex_term.dump_component(),
        label="Complex Termination",
        description="Complex termination: (token usage OR timeout) AND (text mention 'TERMINATE' OR stop message).",
    )

    # Create calculator team
    calc_team = RoundRobinGroupChat(participants=[calc_assistant], termination_condition=calc_or_term)
    builder.add_team(
        calc_team.dump_component(),
        label="RoundRobin Team",
        description="A single AssistantAgent (with a calculator tool) in a RoundRobinGroupChat team. ",
    )

    critic_agent = AssistantAgent(
        name="critic_agent",
        system_message="You are a helpful assistant. Critique the assistant's output and suggest improvements.",
        description="an agent that critiques and improves the assistant's output",
        model_client=base_model,
    )
    selector_default_team = SelectorGroupChat(
        participants=[calc_assistant, critic_agent], termination_condition=calc_or_term, model_client=base_model
    )
    builder.add_team(
        selector_default_team.dump_component(),
        label="Selector Team",
        description="A team with 2 agents - an AssistantAgent (with a calculator tool) and a CriticAgent in a SelectorGroupChat team.",
    )

    # Create Swarm team - agents with handoff capabilities
    # Alice agent with handoff to Bob
    alice_agent = AssistantAgent(
        name="Alice",
        system_message="You are Alice, a helpful assistant. You specialize in general questions. If someone asks about technical topics or needs detailed analysis, hand off to Bob by saying 'Let me hand this over to Bob for a detailed analysis.'",
        model_client=base_model,
        handoffs=["Bob"],
    )

    # Bob agent with handoff back to Alice
    bob_agent = AssistantAgent(
        name="Bob",
        system_message="You are Bob, a technical specialist. You handle detailed technical analysis. If the conversation becomes general or the user needs basic assistance, hand off to Alice by saying 'Let me hand this back to Alice for general assistance.'",
        model_client=base_model,
        handoffs=["Alice"],
    )

    # Create simple Swarm team with handoff-based conversation
    swarm_team = Swarm(participants=[alice_agent, bob_agent], termination_condition=calc_or_term)
    builder.add_team(
        swarm_team.dump_component(),
        label="Swarm Team",
        description="A team with 2 agents (Alice and Bob) that use handoff messages to transfer conversation control between agents based on expertise.",
    )

    # Create web surfer agent
    websurfer_agent = MultimodalWebSurfer(
        name="websurfer_agent",
        description="an agent that solves tasks by browsing the web",
        model_client=base_model,
        headless=True,
    )
    builder.add_agent(
        websurfer_agent.dump_component(),
        label="Web Surfer Agent",
        description="An agent that solves tasks by browsing the web using a headless browser.",
    )

    # Create verification assistant
    verification_assistant = AssistantAgent(
        name="assistant_agent",
        description="an agent that verifies and summarizes information",
        system_message="You are a task verification assistant who is working with a web surfer agent to solve tasks. At each point, check if the task has been completed as requested by the user. If the websurfer_agent responds and the task has not yet been completed, respond with what is left to do and then say 'keep going'. If and only when the task has been completed, summarize and present a final answer that directly addresses the user task in detail and then respond with TERMINATE.",
        model_client=base_model,
    )
    builder.add_agent(
        verification_assistant.dump_component(),
        label="Verification Assistant",
        description="an agent that verifies and summarizes information",
    )

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
        description="A team with 3 agents - a Web Surfer agent that can browse the web, a Verification Assistant that verifies and summarizes information, and a User Proxy that provides human feedback when needed.",
    )

    builder.add_tool(
        tools.generate_image_tool.dump_component(),
        label="Image Generation Tool",
        description="A tool that generates images based on a text description using OpenAI's DALL-E model. Note: Requires OpenAI API key to function.",
    )

    builder.add_tool(
        tools.fetch_webpage_tool.dump_component(),
        label="Fetch Webpage Tool",
        description="A tool that fetches the content of a webpage and converts it to markdown. Requires the requests and beautifulsoup4 library to function.",
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

    code_executor = LocalCommandLineCodeExecutor(work_dir=".coding", timeout=360)
    code_execution_tool = PythonCodeExecutionTool(code_executor)
    builder.add_tool(
        code_execution_tool.dump_component(),
        label="Python Code Execution Tool",
        description="A tool that executes Python code in a local environment.",
    )

    # Create deep research agent
    model_client = OpenAIChatCompletionClient(model="gpt-4o", temperature=0.7)

    research_assistant = AssistantAgent(
        name="research_assistant",
        description="A research assistant that performs web searches and analyzes information",
        model_client=model_client,
        tools=[tools.google_search_tool, tools.fetch_webpage_tool],
        system_message="""You are a research assistant focused on finding accurate information.
        Use the google_search tool to find relevant information.
        Break down complex queries into specific search terms.
        Always verify information across multiple sources when possible.
        When you find relevant information, explain why it's relevant and how it connects to the query. When you get feedback from the a verifier agent, use your tools to act on the feedback and make progress.""",
    )

    verifier = AssistantAgent(
        name="verifier",
        description="A verification specialist who ensures research quality and completeness",
        model_client=model_client,
        system_message="""You are a research verification specialist.
        Your role is to:
        1. Verify that search queries are effective and suggest improvements if needed
        2. Explore drill downs where needed e.g, if the answer is likely in a link in the returned search results, suggest clicking on the link
        3. Suggest additional angles or perspectives to explore. Be judicious in suggesting new paths to avoid scope creep or wasting resources, if the task appears to be addressed and we can provide a report, do this and respond with "TERMINATE".
        4. Track progress toward answering the original question
        5. When the research is complete, provide a detailed summary in markdown format. For incomplete research, end your message with "CONTINUE RESEARCH". For complete research, end your message with APPROVED.
        Your responses should be structured as:
        - Progress Assessment
        - Gaps/Issues (if any)
        - Suggestions (if needed)
        - Next Steps or Final Summary""",
    )

    summary_agent = AssistantAgent(
        name="summary_agent",
        description="A summary agent that provides a detailed markdown summary of the research as a report to the user.",
        model_client=model_client,
        system_message="""You are a summary agent. Your role is to provide a detailed markdown summary of the research as a report to the user. Your report should have a reasonable title that matches the research question and should summarize the key details in the results found in natural an actionable manner. The main results/answer should be in the first paragraph. Where reasonable, your report should have clear comparison tables that drive critical insights. Most importantly, you should have a reference section and cite the key sources (where available) for facts obtained INSIDE THE MAIN REPORT. Also, where appropriate, you may add images if available that illustrate concepts needed for the summary.
        Your report should end with the word "TERMINATE" to signal the end of the conversation.""",
    )

    termination = TextMentionTermination("TERMINATE") | MaxMessageTermination(max_messages=30)

    selector_prompt = """You are coordinating a research team by selecting the team member to speak/act next. The following team member roles are available:
    {roles}.
    The research_assistant performs searches and analyzes information.
    The verifier evaluates progress and ensures completeness.
    The summary_agent provides a detailed markdown summary of the research as a report to the user.

    Given the current context, select the most appropriate next speaker.
    The research_assistant should search and analyze.
    The verifier should evaluate progress and guide the research (select this role is there is a need to verify/evaluate progress). You should ONLY select the summary_agent role if the research is complete and it is time to generate a report.

    Base your selection on:
    1. Current stage of research
    2. Last speaker's findings or suggestions
    3. Need for verification vs need for new information
    Read the following conversation. Then select the next role from {participants} to play. Only return the role.

    {history}

    Read the above conversation. Then select the next role from {participants} to play. ONLY RETURN THE ROLE."""

    deep_research_team = SelectorGroupChat(
        participants=[research_assistant, verifier, summary_agent],
        model_client=model_client,
        termination_condition=termination,
        selector_prompt=selector_prompt,
        allow_repeated_speaker=True,
    )

    builder.add_team(
        deep_research_team.dump_component(),
        label="Deep Research Team",
        description="A team with 3 agents - a Research Assistant that performs web searches and analyzes information, a Verifier that ensures research quality and completeness, and a Summary Agent that provides a detailed markdown summary of the research as a report to the user.",
    )

    # Create a cost-controlled team using token usage termination
    cost_controlled_assistant = AssistantAgent(
        name="budget_assistant",
        system_message="You are a helpful assistant with a strict token budget. Be concise and efficient in your responses. When done, say TERMINATE.",
        model_client=base_model,
        tools=[tools.calculator_tool],
    )

    # Combine token usage limit with text termination for safety
    budget_termination = TokenUsageTermination(max_total_token=500) | TextMentionTermination(text="TERMINATE")

    budget_team = RoundRobinGroupChat(
        participants=[cost_controlled_assistant], termination_condition=budget_termination
    )

    builder.add_team(
        budget_team.dump_component(),
        label="Budget-Controlled Team",
        description="A cost-controlled team that terminates when token usage exceeds 500 tokens or when 'TERMINATE' is mentioned.",
    )

    # Create a time-limited team for quick responses
    quick_assistant = AssistantAgent(
        name="quick_assistant",
        system_message="You are a quick response assistant. Provide fast, accurate answers within the time limit.",
        model_client=base_model,
    )

    # 30-second timeout with fallback termination
    quick_termination = TimeoutTermination(timeout_seconds=30) | MaxMessageTermination(max_messages=5)

    quick_team = RoundRobinGroupChat(participants=[quick_assistant], termination_condition=quick_termination)

    builder.add_team(
        quick_team.dump_component(),
        label="Quick Response Team",
        description="A time-limited team that provides quick responses within 30 seconds or 5 messages maximum.",
    )

    # Add workbenches to the gallery

    # Create a static workbench with basic tools
    static_workbench = StaticWorkbench(tools=[tools.calculator_tool, tools.fetch_webpage_tool])
    builder.add_workbench(
        static_workbench.dump_component(),
        label="Basic Tools Workbench",
        description="A static workbench containing basic tools like calculator and webpage fetcher for common tasks.",
    )

    # Create an MCP workbench for fetching web content using mcp-server-fetch
    # Note: This requires uv to be installed (comes with uv package manager)
    fetch_server_params = StdioServerParams(
        command="uv",
        args=["tool", "run", "mcp-server-fetch"],
        read_timeout_seconds=60,
    )
    mcp_workbench = McpWorkbench(server_params=fetch_server_params)
    builder.add_workbench(
        mcp_workbench.dump_component(),
        label="MCP Fetch Workbench",
        description="An MCP workbench that provides web content fetching capabilities using the mcp-server-fetch MCP server. Allows agents to fetch and read content from web pages and APIs.",
    )

    # Create an MCP workbench with StreamableHttpServerParams for HTTP-based MCP servers
    # Note: This is an example - adjust URL and authentication as needed
    streamable_server_params = StreamableHttpServerParams(
        url="http://localhost:8005/mcp",
        headers={"Authorization": "Bearer your-api-key", "Content-Type": "application/json"},
        timeout=30,
        sse_read_timeout=60 * 5,
        terminate_on_close=True,
    )
    streamable_mcp_workbench = McpWorkbench(server_params=streamable_server_params)
    builder.add_workbench(
        streamable_mcp_workbench.dump_component(),
        label="MCP Streamable HTTP Workbench",
        description="An MCP workbench that connects to HTTP-based MCP servers using Server-Sent Events (SSE). Suitable for cloud-hosted MCP services and custom HTTP MCP implementations.",
    )

    # Create an MCP workbench for filesystem operations
    # Note: This requires npx to be installed and allows access to specified directories
    filesystem_server_params = StdioServerParams(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/Users", "/tmp"],
        read_timeout_seconds=60,
    )
    filesystem_mcp_workbench = McpWorkbench(server_params=filesystem_server_params)
    builder.add_workbench(
        filesystem_mcp_workbench.dump_component(),
        label="MCP Filesystem Workbench",
        description="An MCP workbench that provides filesystem access capabilities using the @modelcontextprotocol/server-filesystem MCP server. Allows agents to read, write, and manage files and directories within specified allowed paths.",
    )

    # Create an MCP workbench for testing with everything server
    # Note: This requires npx to be installed and provides comprehensive MCP testing tools
    everything_server_params = StdioServerParams(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-everything"],
        read_timeout_seconds=60,
    )
    everything_mcp_workbench = McpWorkbench(server_params=everything_server_params)
    builder.add_workbench(
        everything_mcp_workbench.dump_component(),
        label="MCP Test Server",
        description="An MCP workbench that provides comprehensive testing tools using the @modelcontextprotocol/server-everything MCP server. Includes various tools for testing MCP functionality, protocol features, and capabilities.",
    )

    return builder.build()


def create_default_lite_team():
    """Create a simple default team for lite mode - a basic assistant with calculator tool."""
    import json
    import os
    import tempfile

    # model clients require API keys to be set in the environment or passed in
    # as arguments. For testing purposes, we set them to "test" if not already set.
    for key in ["OPENAI_API_KEY", "AZURE_OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
        if not os.environ.get(key):
            os.environ[key] = "test"

    # Create base model client
    base_model = OpenAIChatCompletionClient(model="gpt-4o-mini")

    # Create assistant agent with calculator tool
    assistant = AssistantAgent(
        name="assistant",
        model_client=base_model,
        tools=[tools.calculator_tool],
    )

    # Create termination condition
    termination = TextMentionTermination(text="TERMINATE") | MaxMessageTermination(max_messages=5)

    # Create simple round robin team
    team = RoundRobinGroupChat(participants=[assistant], termination_condition=termination)

    # Create temporary file with team data
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(team.dump_component().model_dump(), f, indent=2)
        return f.name


if __name__ == "__main__":
    # Create and save the gallery
    gallery = create_default_gallery()

    # Save to file
    with open("gallery_default.json", "w") as f:
        f.write(gallery.model_dump_json(indent=2))
