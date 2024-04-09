import functools

from textual import work
from textual.reactive import reactive
from textual.app import ComposeResult
from textual.widgets import Collapsible, Static, Markdown, Label
from textual.containers import ScrollableContainer, Container

from ..widgets.custom_widgets import NamedLoadingIndicator
from ..profiler.profiler import Profiler, ChatProfile, MessageProfile, State


class ProfileNode(Static):

    message_profile: MessageProfile

    DEFAULT_CSS = """
    ProfileNode Markdown {
        border: solid $primary;
        padding: 1;
    }
    """

    def compose(self) -> ComposeResult:
        states = self.message_profile.states

        def state_name_comparator(x: State, y: State):
            return x.name < y.name

        states.sort(key=functools.cmp_to_key(state_name_comparator))

        state_display_str = " ".join([str(state) for state in states])

        with Collapsible(collapsed=True, title=state_display_str):
            yield Static(str(self.message_profile))
            yield Markdown(str(self.message_profile.message))


class ProfileDiagram(ScrollableContainer):

    chat_profile: ChatProfile = reactive(None, recompose=True)

    def compose(self) -> ComposeResult:

        if self.chat_profile is None:
            yield NamedLoadingIndicator(text="Profiling")
            return

        num_messages = self.chat_profile.num_messages
        yield Label(f"Number of messages: {num_messages}", classes="heading")
        for message_profile in self.chat_profile.message_profiles:
            node = ProfileNode()
            node.message_profile = message_profile
            yield node


class ProfilerContainer(Container):

    chat_history = reactive(None)
    profile_diagram = None

    def __init__(self, *args, root_id: int = -1, **kwargs):
        super().__init__(*args, **kwargs)
        self.root_id = root_id

    def on_mount(self) -> None:
        self.set_interval(1, self.update_chat_history)

    async def update_chat_history(self) -> None:
        dbm = self.app.config.db_manager
        self.chat_history = await dbm.get_chat_history(self.root_id)

    def watch_chat_history(self, new_chat_history) -> None:
        if new_chat_history is None:
            return

        self.start_profiling()

    @work(thread=True, exclusive=True)
    async def start_profiling(self):
        chat_profile = await self.profile_chat()
        if self.profile_diagram is None:
            self.profile_diagram = ProfileDiagram()
        self.profile_diagram.chat_profile = chat_profile

    async def profile_chat(self) -> ChatProfile:
        llm_service = self.app.config.llm_service
        profiler = Profiler(llm_service=llm_service)

        message_profile_list = []

        for message in self.chat_history.messages:
            msg_profile = profiler.profile_message(message)
            message_profile_list.append(msg_profile)

        chat_profile = ChatProfile(num_messages=len(self.chat_history.messages), message_profiles=message_profile_list)

        return chat_profile

    def compose(self):
        if self.profile_diagram is None:
            self.profile_diagram = ProfileDiagram()
        yield self.profile_diagram
