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


class PrefLearningWidget(Static):

    DEFAULT_CSS = """
    PrefLearningWidget {
        layout: grid;
        grid-size: 1 2;
        grid-rows: 1fr 4;
        grid-gutter: 1 2;
    }

    #pref-learning-editor {
        width: 100%;
        height: 100%;
        content-align: center middle;
    }

    #pref-learning-footer{
        align: center middle;
    }

    #pref-screen-footer Button {
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
        yield TextArea.code_editor("", language="python", id="pref-learning-editor")
        with Horizontal(id="pref-learning-footer"):
            yield Button("Append Preferences", variant="primary", id="save-learned-pref")

    @work(thread=True)
    async def start_learning(self) -> None:
        widget = self.query_one("#pref-learning-editor", TextArea)
        widget.text = "# Learning preferences/advice..."

        history = self.history
        pref = learn_pref_from_history(self.app_config.llm_service, history)

        widget.text = pref

    @on(Button.Pressed, "#save-learned-pref")
    async def save(self) -> None:
        widget = self.query_one("#pref-learning-editor", TextArea)
        new_pref = widget.text

        try:
            user = await self.app_config.db_manager.get_user()
            user.preferences = user.preferences + "\n" + new_pref
            await self.app_config.db_manager.set_user(user)
        except Exception as e:
            error_message = f"{e}"
            self.post_message(UserNotificationError(error_message))
            return
        else:
            self.post_message(UserNotificationSuccess("Add new preferences"))


def learn_pref_from_history(llm_service: ChatCompletionService, history: ChatHistory) -> str:

    markdown = ""
    for msg in history.messages:
        markdown += f"{msg.role}: {msg.content}\n"

    messages = [
        OpenAIMessage(
            role="system",
            content="""You are a helpful assistant that for the given chat
            history can return list of concise lessons and advice.

            Try to extract a most general version of advice based on the chat history.
            That can be reused in the future for similar tasks.

            The chat history contains a task the agents were trying to accomplish.
            Analyze the following chat history to assess if the task was completed,
            and if it was return the python function that would accomplish the task.
        """,
        ),
        OpenAIMessage(
            role="user",
            content=f"""The chat history is

            {markdown}

            Only generate 1-2 bullet list of preferences.
            Make sure the advice is useful for an agent to following in the future.
            Advice should be directed as something that could help the agent write better
            code in the future.
            """,
        ),
    ]

    response: OpenAIMessage = llm_service.create(messages)

    return response.content
