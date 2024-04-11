from textual import work, on
from textual.app import ComposeResult
from textual.widgets import TextArea, Button, Static
from textual.containers import Horizontal

from autogen.code_utils import extract_code

from ...tools import Tool
from ...database.database import ChatHistory
from ...llm import ChatCompletionService, OpenAIMessage
from ...app_config import AppConfiguration
from ...messages import UserNotificationError, UserNotificationSuccess


class ToolLearningWidget(Static):

    DEFAULT_CSS = """
    ToolLearningWidget {
        layout: grid;
        grid-size: 1 2;
        grid-gutter: 1 2;
        grid-rows: 1fr 4;
    }

    #tool-learning-editor {
        width: 100%;
        height: 100%;
        content-align: center middle;
    }

    #tool-learning-footer{
        align: center middle;
    }

    #learning-screen-footer Button {
        margin: 1;
    }

    """

    def __init__(self, history: ChatHistory = None, app_config: AppConfiguration = None, **kwargs):
        super().__init__(**kwargs)
        self.history = history
        self.app_config = app_config

    async def on_mount(self) -> None:
        self.start_learning()

    def compose(self) -> ComposeResult:
        yield TextArea.code_editor("", language="python", id="tool-learning-editor")
        with Horizontal(id="tool-learning-footer"):
            yield Button("Save", variant="primary", id="save-learned-tool")

    @work(thread=True)
    async def start_learning(self) -> None:
        widget = self.query_one("#tool-learning-editor", TextArea)
        widget.text = "# Learning..."

        history = self.history
        name, code = learn_tool_from_history(self.app_config.llm_service, history)

        widget.text = "#" + name + "\n" + code

    @on(Button.Pressed, "#save-learned-tool")
    async def save(self) -> None:
        widget = self.query_one("#tool-learning-editor", TextArea)
        code = widget.text
        name = code.split("\n")[0][1:]

        tool = Tool(name=name, code=code)
        try:
            tool.validate_tool()
            await self.app_config.db_manager.set_tool(tool)
        except Exception as e:
            error_message = f"{e}"
            self.post_message(UserNotificationError(error_message))
            return
        else:
            self.post_message(UserNotificationSuccess(f"New tool {tool.name} saved successfully"))


def learn_tool_from_history(llm_service: ChatCompletionService, history: ChatHistory) -> str:

    markdown = ""
    for msg in history.messages:
        markdown += f"{msg.role}: {msg.content}\n"

    messages = [
        OpenAIMessage(
            role="system",
            content="""You are a helpful assistant that for the given chat
            history can return a standalone, documented python function.

            Try to extract a most general version of the function based on the chat history.
            That can be reused in the future for similar tasks. Eg do not use hardcoded arguments.
            Instead make them function parameters.

            The chat history contains a task the agents were trying to accomplish.
            Analyze the following chat history to assess if the task was completed,
            and if it was return the python function that would accomplish the task.
        """,
        ),
        OpenAIMessage(
            role="user",
            content=f"""The chat history is

            {markdown}

            Only generate a single python function in code blocks and nothing else.
            Make sure all imports are inside the function.
            Both ast.FunctionDef, ast.AsyncFunctionDef are acceptable.

            Function signature should be annotated properly.
            Function should return a string as the final result.
            """,
        ),
    ]

    response: OpenAIMessage = llm_service.create(messages)

    # extract a code block from the reply
    code_blocks = extract_code(response.content)
    lang, code = code_blocks[0]

    messages.append(OpenAIMessage(role="assistant", content=code))

    messages.append(
        OpenAIMessage(
            role="user",
            content="""suggest a max two word english phrase that is a friendly
            display name for the function. Only reply with the name for the code block.
            no need to use an quotes or code blocks. Just two words.""",
        )
    )

    response: OpenAIMessage = llm_service.create(messages)
    name = response.content.strip()

    return name, code
