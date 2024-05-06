from .state import State, StateSpace


AGB_STATE_SPACE = StateSpace(
    states={
        State(
            name="USER-REQUEST",
            description="The message shows the *user* requesting a task that needs to be completed",
        ),
        State(
            name="CODING",
            description="The message shows the assistant writing python or shell code to solve a problem. IE the message contains code blocks. This code does not apply to markdown code blocks",
        ),
        State(
            name="PLANNING",
            description="The message shows that the agent is create a step by step plan to accomplish some task.",
        ),
        State(
            name="ANALYSING-RESULTS",
            description="The assistant's message is reflecting on results obtained so far",
        ),
        State(
            name="CODE-EXECUTION",
            description="The user shared results of code execution, e.g., results, logs, error trace",
        ),
        State(
            name="CODE-EXECUTION-ERROR",
            description="The user shared results of code execution and they show an error in execution",
        ),
        State(
            name="CODE-EXECUTION-SUCCESS",
            description="The user shared results of code execution and they show a successful execution",
        ),
        State(
            name="CODING-TOOL-USE",
            description="The message contains a code block and the code uses method from the `functions` module eg indicated by presence of `from functions import....`",
        ),
        State(
            name="ASKING-FOR-INFO",
            description="The assistant is asking a question",
        ),
        State(
            name="SUMMARIZING",
            description="The assistant is synthesizing/summarizing information gathered so far",
        ),
        State(
            name="TERMINATE",
            description="The agent's message contains the word 'TERMINATE'",
        ),
        State(
            name="EMPTY",
            description="The message is empty",
        ),
        State(
            name="UNDEFINED",
            description="Use this code when the message does not fit any of the other codes",
        ),
        # states for web surfing
        State(
            name="WEB-SEARCH",
            description="Searching the web",
        ),
        State(
            name="CLICK-ON-LINK",
            description="Clicking on a link",
        ),
        State(
            name="CLICK-ON-BUTTON",
            description="Clicking on a button",
        ),
        State(
            name="LOGGING-IN",
            description="Logging into a website",
        ),
        State(
            name="WEBPAGE-TYPING",
            description="Typing text",
        ),
        State(
            name="WEBPAGE-SCROLLING",
            description="Scrolling the page",
        ),
    }
)
