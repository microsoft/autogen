from textual import work
from textual.app import ComposeResult
from textual.widgets import Label, TextArea, Button
from textual.containers import ScrollableContainer, Grid, Horizontal

from ..llm import ChatCompletionService, OpenAIMessage
from ..database.database import ChatHistory

from autogen.code_utils import extract_code


class LearningTab(Grid):

    def __init__(self, *args, root_id: int = -1, **kwargs):
        super().__init__(*args, **kwargs)
        self.root_msg_id = root_id

    def compose(self) -> ComposeResult:
        with Grid(id="learning-screen"):
            yield Horizontal(Label("Interactive Tool Learning", classes="heading"), id="learning-screen-header")
            yield ScrollableContainer(
                TextArea.code_editor(
                    f"""
                    # Learning a function for {self.root_msg_id}
                    """,
                    language="python",
                ),
                id="learning-screen-contents",
            )
            with Horizontal(id="learning-screen-footer"):
                # yield Button("Start", variant="error", id="start-learning")
                yield Button("Save", variant="primary", id="save")

    def on_mount(self) -> None:
        self.start_learning()

    # @on(Button.Pressed, "#save")
    # def save(self) -> None:
    #     widget = self.query_one("#learning-screen-contents > TextArea", TextArea)
    #     code = widget.text
    #     name = code.split("\n")[0][1:]

    #     tool = Tool(name, code)
    #     try:
    #         tool.validate_tool()
    #         APP_CONFIG.update_tool(tool)
    #         self.app.pop_screen()
    #         self.app.push_screen(NotificationScreen(message="Tool saved successfully"))

    #     except InvalidToolError as e:
    #         error_message = f"{e}"
    #         self.post_message(UserNotificationError(error_message))
    #         return

    #     except ToolUpdateError as e:
    #         error_message = f"{e}"
    #         self.post_message(UserNotificationError(error_message))
    #         return

    @work(thread=True)
    async def start_learning(self) -> None:
        widget = self.query_one("#learning-screen-contents > TextArea", TextArea)
        widget.text = "# Learning..."

        dbm = self.app.config.db_manager

        history = await dbm.get_chat_history(self.root_msg_id)
        name, code = learn_tool_from_history(self.app.config.llm_service, history)
        # name, code = "Test function", "def test_function():\n    return 'Hello, World!'"

        widget.text = "#" + name + "\n" + code


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
