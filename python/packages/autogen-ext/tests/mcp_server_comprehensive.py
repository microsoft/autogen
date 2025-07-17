import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from mcp import PromptsCapability, ResourcesCapability, ServerCapabilities, ToolsCapability
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    GetPromptResult,
    Prompt,
    PromptArgument,
    PromptMessage,
    Resource,
    TextContent,
    Tool,
)
from pydantic import AnyUrl

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample data for demonstration
SAMPLE_DATA = {
    "users": [
        {"id": 1, "name": "Alice", "email": "alice@example.com", "department": "Engineering"},
        {"id": 2, "name": "Bob", "email": "bob@example.com", "department": "Sales"},
        {"id": 3, "name": "Charlie", "email": "charlie@example.com", "department": "Marketing"},
    ],
    "projects": [
        {"id": 1, "name": "Project Alpha", "status": "active", "team_size": 5},
        {"id": 2, "name": "Project Beta", "status": "completed", "team_size": 3},
        {"id": 3, "name": "Project Gamma", "status": "planning", "team_size": 2},
    ],
}


class SimpleMcpServer:
    """A simple MCP server demonstrating basic functionality."""

    def __init__(self) -> None:
        self.server: Server[object] = Server("simple-mcp-server")
        self.register_handlers()  # type: ignore[no-untyped-call]

    def register_handlers(self) -> None:
        """Register all MCP handlers."""

        # Prompts
        @self.server.list_prompts()  # type: ignore[no-untyped-call,misc]
        async def list_prompts() -> list[Prompt]:  # pyright: ignore[reportUnusedFunction]
            """List available prompts."""
            return [
                Prompt(
                    name="code_review",
                    description="Generate a comprehensive code review for a given piece of code",
                    arguments=[
                        PromptArgument(
                            name="code",
                            description="The code to review",
                            required=True,
                        ),
                        PromptArgument(
                            name="language",
                            description="Programming language of the code",
                            required=True,
                        ),
                    ],
                ),
                Prompt(
                    name="documentation",
                    description="Generate documentation for code or APIs",
                    arguments=[
                        PromptArgument(
                            name="content",
                            description="The content to document",
                            required=True,
                        ),
                    ],
                ),
            ]

        @self.server.get_prompt()  # type: ignore[no-untyped-call,misc]
        async def get_prompt(name: str, arguments: Optional[Dict[str, str]] = None) -> GetPromptResult:  # pyright: ignore[reportUnusedFunction]
            """Get a specific prompt with arguments."""
            if not arguments:
                arguments = {}

            if name == "code_review":
                code = arguments.get("code", "// No code provided")
                language = arguments.get("language", "unknown")

                return GetPromptResult(
                    description=f"Code review for {language} code",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(
                                type="text",
                                text=f"Please review this {language} code:\n\n```{language}\n{code}\n```",
                            ),
                        ),
                    ],
                )

            elif name == "documentation":
                content = arguments.get("content", "No content provided")

                return GetPromptResult(
                    description="Documentation generation",
                    messages=[
                        PromptMessage(
                            role="user",
                            content=TextContent(
                                type="text",
                                text=f"Please generate documentation for:\n\n{content}",
                            ),
                        ),
                    ],
                )

            else:
                raise ValueError(f"Unknown prompt: {name}")

        # Resources
        @self.server.list_resources()  # type: ignore[no-untyped-call,misc]
        async def list_resources() -> list[Resource]:  # pyright: ignore[reportUnusedFunction]
            """List available resources."""
            return [
                Resource(
                    uri=AnyUrl("file:///company/users.json"),
                    name="Company Users",
                    description="List of all company users",
                    mimeType="application/json",
                ),
                Resource(
                    uri=AnyUrl("file:///company/projects.json"),
                    name="Active Projects",
                    description="Current projects",
                    mimeType="application/json",
                ),
            ]

        @self.server.read_resource()  # type: ignore[no-untyped-call,misc]
        async def read_resource(uri: AnyUrl) -> str:  # pyright: ignore[reportUnusedFunction]
            """Read a specific resource."""
            uri_str = str(uri)

            if uri_str == "file:///company/users.json":
                return json.dumps(SAMPLE_DATA["users"], indent=2)

            elif uri_str == "file:///company/projects.json":
                return json.dumps(SAMPLE_DATA["projects"], indent=2)

            else:
                raise ValueError(f"Unknown resource: {uri_str}")

        # Tools
        @self.server.list_tools()  # type: ignore[no-untyped-call,misc]
        async def list_tools() -> list[Tool]:  # pyright: ignore[reportUnusedFunction]
            """List available tools."""
            return [
                Tool(
                    name="echo",
                    description="Echo back the input text",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "text": {
                                "type": "string",
                                "description": "Text to echo back",
                            }
                        },
                        "required": ["text"],
                    },
                ),
                Tool(
                    name="get_time",
                    description="Get the current time",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                    },
                ),
            ]

        @self.server.call_tool()  # type: ignore[no-untyped-call,misc]
        async def call_tool(name: str, arguments: Optional[Dict[str, Any]] = None) -> list[TextContent]:  # pyright: ignore[reportUnusedFunction]
            """Call a specific tool."""
            if not arguments:
                arguments = {}

            if name == "echo":
                text = arguments.get("text", "")
                return [
                    TextContent(
                        type="text",
                        text=f"Echo: {text}",
                    )
                ]

            elif name == "get_time":
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                return [
                    TextContent(
                        type="text",
                        text=f"Current time: {current_time}",
                    )
                ]

            else:
                raise ValueError(f"Unknown tool: {name}")

    async def run(self) -> None:
        """Run the MCP server."""
        # Server capabilities
        init_options = InitializationOptions(
            server_name="simple-mcp-server",
            server_version="1.0.0",
            capabilities=ServerCapabilities(
                prompts=PromptsCapability(listChanged=True),
                resources=ResourcesCapability(
                    subscribe=True,
                    listChanged=True,
                ),
                tools=ToolsCapability(listChanged=True),
            ),
        )

        # Run the server
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                init_options,
            )


async def main() -> None:
    """Main entry point."""
    server: SimpleMcpServer = SimpleMcpServer()
    await server.run()  # type: ignore[no-untyped-call]


if __name__ == "__main__":
    asyncio.run(main())  # type: ignore[no-untyped-call]
