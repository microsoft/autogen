"""From: https://github.com/modelcontextprotocol/python-sdk?tab=readme-ov-file#elicitation"""

from pathlib import Path

from mcp import SamplingMessage
from mcp.server.fastmcp import Context, FastMCP
from mcp.types import TextContent
from pydantic import BaseModel, Field

mcp = FastMCP(name="Elicitation Example")


class BookingPreferences(BaseModel):
    """Schema for collecting user preferences."""

    checkAlternative: bool = Field(description="Would you like to check another time?")
    alternativeTime: str = Field(
        description="Alternative time.",
    )


@mcp.tool()
async def book_table(
    time: str,
    party_size: int,
    ctx: Context,
) -> str:
    """Book a table with time availability check."""
    # time unavailable - ask user for alternative
    result = await ctx.elicit(
        message=(f"No tables available for {party_size} at {time}. Would you like to try another time?"),
        schema=BookingPreferences,
    )

    if result.action == "accept" and result.data:
        if result.data.checkAlternative:
            return f"[SUCCESS] Booked for {result.data.alternativeTime}"
        return "[CANCELLED] No booking made"
    return "[CANCELLED] Booking cancelled"


@mcp.tool()
async def list_dir(path: Path, ctx: Context) -> list[str]:
    """List the files and directories in path"""
    roots = await ctx.session.list_roots()
    for root in roots.roots:
        root_path = root.uri.path
        if root_path:
            root_path = Path(root_path)
            try:
                _ = path.relative_to(root_path)
                return ["Downloads", "Documents", "image.png", "presentation.pptx"]
            except ValueError:
                # Skip relative_to failure
                pass
    raise ValueError(f"Cannot list_dir in {path} because it is not a child of the available roots.")


@mcp.tool()
async def generate_poem(topic: str, ctx: Context) -> str:
    poem = await ctx.session.create_message(
        [SamplingMessage(role="user", content=TextContent(type="text", text=f"Write a poem about {topic}."))],
        max_tokens=100,
        system_prompt="You are a very creative poet.",
        temperature=0.8,
        stop_sequences=["\n\n"],
    )
    if isinstance(poem.content, TextContent):
        return poem.content.text
    else:
        raise TypeError(f"Unrecognized message response type {type(poem.content).__name__}")


if __name__ == "__main__":
    mcp.run("stdio")
