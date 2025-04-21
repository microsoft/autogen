from typing import Any, Optional

from autogen_core import CancellationToken
from autogen_core.memory import (
    Memory,
    MemoryContent,
    MemoryMimeType,
    MemoryQueryResult,
    UpdateContextResult,
)
from autogen_core.model_context import ChatCompletionContext
from autogen_core.models import SystemMessage

from ._canvas_writer import ApplyPatchTool, UpdateFileTool
from ._text_canvas import TextCanvas


class TextCanvasMemory(Memory):
    """
    A memory implementation that uses a Canvas for storing file-like content.
    Inserts the current state of the canvas into the ChatCompletionContext on each turn.

    ... warning::

        This is an experimental API and may change in the future.

    The TextCanvasMemory provides a persistent, file-like storage mechanism that can be used
    by agents to read and write content. It automatically injects the current state of all files
    in the canvas into the model context before each inference.

    This is particularly useful for:
    - Allowing agents to create and modify documents over multiple turns
    - Enabling collaborative document editing between multiple agents
    - Maintaining persistent state across conversation turns
    - Working with content too large to fit in a single message

    The canvas provides tools for:
    - Creating or updating files with new content
    - Applying patches (unified diff format) to existing files

    Examples:

        **Example: Using TextCanvasMemory with an AssistantAgent**

        The following example demonstrates how to create a TextCanvasMemory and use it with
        an AssistantAgent to write and update a story file.

        .. code-block:: python

            import asyncio
            from autogen_core import CancellationToken
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.messages import TextMessage
            from autogen_ext.memory.canvas import TextCanvasMemory


            async def main():
                # Create a model client
                model_client = OpenAIChatCompletionClient(
                    model="gpt-4o",
                    # api_key = "your_openai_api_key"
                )

                # Create the canvas memory
                text_canvas_memory = TextCanvasMemory()

                # Get tools for working with the canvas
                update_file_tool = text_canvas_memory.get_update_file_tool()
                apply_patch_tool = text_canvas_memory.get_apply_patch_tool()

                # Create an agent with the canvas memory and tools
                writer_agent = AssistantAgent(
                    name="Writer",
                    model_client=model_client,
                    description="A writer agent that creates and updates stories.",
                    system_message='''
                    You are a Writer Agent. Your focus is to generate a story based on the user's request.

                    Instructions for using the canvas:

                    - The story should be stored on the canvas in a file named "story.md".
                    - If "story.md" does not exist, create it by calling the 'update_file' tool.
                    - If "story.md" already exists, generate a unified diff (patch) from the current
                      content to the new version, and call the 'apply_patch' tool to apply the changes.

                    IMPORTANT: Do not include the full story text in your chat messages.
                    Only write the story content to the canvas using the tools.
                    ''',
                    tools=[update_file_tool, apply_patch_tool],
                    memory=[text_canvas_memory],
                )

                # Send a message to the agent
                await writer_agent.on_messages(
                    [TextMessage(content="Write a short story about a bunny and a sunflower.", source="user")],
                    CancellationToken(),
                )

                # Retrieve the content from the canvas
                story_content = text_canvas_memory.canvas.get_latest_content("story.md")
                print("Story content from canvas:")
                print(story_content)


            if __name__ == "__main__":
                asyncio.run(main())

        **Example: Using TextCanvasMemory with multiple agents**

        The following example shows how to use TextCanvasMemory with multiple agents
        collaborating on the same document.

        .. code-block:: python

            import asyncio
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.teams import RoundRobinGroupChat
            from autogen_agentchat.conditions import TextMentionTermination
            from autogen_ext.memory.canvas import TextCanvasMemory


            async def main():
                # Create a model client
                model_client = OpenAIChatCompletionClient(
                    model="gpt-4o",
                    # api_key = "your_openai_api_key"
                )

                # Create the shared canvas memory
                text_canvas_memory = TextCanvasMemory()
                update_file_tool = text_canvas_memory.get_update_file_tool()
                apply_patch_tool = text_canvas_memory.get_apply_patch_tool()

                # Create a writer agent
                writer_agent = AssistantAgent(
                    name="Writer",
                    model_client=model_client,
                    description="A writer agent that creates stories.",
                    system_message="You write children's stories on the canvas in story.md.",
                    tools=[update_file_tool, apply_patch_tool],
                    memory=[text_canvas_memory],
                )

                # Create a critique agent
                critique_agent = AssistantAgent(
                    name="Critique",
                    model_client=model_client,
                    description="A critique agent that provides feedback on stories.",
                    system_message="You review the story.md file and provide constructive feedback.",
                    memory=[text_canvas_memory],
                )

                # Create a team with both agents
                team = RoundRobinGroupChat(
                    participants=[writer_agent, critique_agent],
                    termination_condition=TextMentionTermination("TERMINATE"),
                    max_turns=10,
                )

                # Run the team on a task
                await team.run(task="Create a children's book about a bunny and a sunflower")

                # Get the final story
                story = text_canvas_memory.canvas.get_latest_content("story.md")
                print(story)


            if __name__ == "__main__":
                asyncio.run(main())
    """

    def __init__(self, canvas: Optional[TextCanvas] = None):
        super().__init__()
        self.canvas = canvas if canvas is not None else TextCanvas()

    async def update_context(self, model_context: ChatCompletionContext) -> UpdateContextResult:
        """
        Inject the entire canvas summary (or a selected subset) as reference data.
        Here, we just put it into a system message, but you could customize.
        """
        snapshot = self.canvas.get_all_contents_for_context()
        if snapshot.strip():
            msg = SystemMessage(content=snapshot)
            await model_context.add_message(msg)

            # Return it for debugging/logging
            memory_content = MemoryContent(content=snapshot, mime_type=MemoryMimeType.TEXT)
            return UpdateContextResult(memories=MemoryQueryResult(results=[memory_content]))

        return UpdateContextResult(memories=MemoryQueryResult(results=[]))

    async def query(
        self, query: str | MemoryContent, cancellation_token: Optional[CancellationToken] = None, **kwargs: Any
    ) -> MemoryQueryResult:
        """
        Potentially search for matching filenames or file content.
        This example returns empty.
        """
        return MemoryQueryResult(results=[])

    async def add(self, content: MemoryContent, cancellation_token: Optional[CancellationToken] = None) -> None:
        """
        Example usage: Possibly interpret content as a patch or direct file update.
        Could also be done by a specialized "CanvasTool" instead.
        """
        # NO-OP here, leaving actual changes to the CanvasTool
        pass

    async def clear(self) -> None:
        """Clear the entire canvas by replacing it with a new empty instance."""
        # Create a new TextCanvas instance instead of calling __init__ directly
        self.canvas = TextCanvas()

    async def close(self) -> None:
        pass

    def get_update_file_tool(self) -> UpdateFileTool:
        """
        Returns an UpdateFileTool instance that works with this memory's canvas.
        """
        return UpdateFileTool(self.canvas)

    def get_apply_patch_tool(self) -> ApplyPatchTool:
        """
        Returns an ApplyPatchTool instance that works with this memory's canvas.
        """
        return ApplyPatchTool(self.canvas)
