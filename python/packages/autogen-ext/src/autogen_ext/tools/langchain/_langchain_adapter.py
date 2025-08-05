from __future__ import annotations

import asyncio
import inspect
from typing import TYPE_CHECKING, Any, Callable, Dict, Type, cast

from autogen_core import CancellationToken
from autogen_core.tools import BaseTool
from pydantic import BaseModel, Field, create_model

if TYPE_CHECKING:
    from langchain_core.tools import BaseTool as LangChainTool


class LangChainToolAdapter(BaseTool[BaseModel, Any]):
    """Allows you to wrap a LangChain tool and make it available to AutoGen.

    .. note::

        This class requires the :code:`langchain` extra for the :code:`autogen-ext` package.

        .. code-block:: bash

            pip install -U "autogen-ext[langchain]"


    Args:
        langchain_tool (LangChainTool): A LangChain tool to wrap

    Examples:

        Use the `PythonAstREPLTool` from the `langchain_experimental` package to
        create a tool that allows you to interact with a Pandas DataFrame.

        .. code-block:: python

            import asyncio
            import pandas as pd
            from langchain_experimental.tools.python.tool import PythonAstREPLTool
            from autogen_ext.tools.langchain import LangChainToolAdapter
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_agentchat.messages import TextMessage
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.ui import Console
            from autogen_core import CancellationToken


            async def main() -> None:
                df = pd.read_csv("https://raw.githubusercontent.com/pandas-dev/pandas/main/doc/data/titanic.csv")  # type: ignore
                tool = LangChainToolAdapter(PythonAstREPLTool(locals={"df": df}))
                model_client = OpenAIChatCompletionClient(model="gpt-4o")
                agent = AssistantAgent(
                    "assistant",
                    tools=[tool],
                    model_client=model_client,
                    system_message="Use the `df` variable to access the dataset.",
                )
                await Console(
                    agent.on_messages_stream(
                        [TextMessage(content="What's the average age of the passengers?", source="user")], CancellationToken()
                    )
                )


            asyncio.run(main())

        This example demonstrates how to use the `SQLDatabaseToolkit` from the `langchain_community`
        package to interact with an SQLite database.
        It uses the :class:`~autogen_agentchat.team.RoundRobinGroupChat` to iterate the single agent over multiple steps.
        If you want to one step at a time, you can just call `run_stream` method of the
        :class:`~autogen_agentchat.agents.AssistantAgent` class directly.

        .. code-block:: python

            import asyncio
            import sqlite3

            import requests
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.conditions import TextMentionTermination
            from autogen_agentchat.teams import RoundRobinGroupChat
            from autogen_agentchat.ui import Console
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_ext.tools.langchain import LangChainToolAdapter
            from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
            from langchain_community.utilities.sql_database import SQLDatabase
            from langchain_openai import ChatOpenAI
            from sqlalchemy import Engine, create_engine
            from sqlalchemy.pool import StaticPool


            def get_engine_for_chinook_db() -> Engine:
                url = "https://raw.githubusercontent.com/lerocha/chinook-database/master/ChinookDatabase/DataSources/Chinook_Sqlite.sql"
                response = requests.get(url)
                sql_script = response.text
                connection = sqlite3.connect(":memory:", check_same_thread=False)
                connection.executescript(sql_script)
                return create_engine(
                    "sqlite://",
                    creator=lambda: connection,
                    poolclass=StaticPool,
                    connect_args={"check_same_thread": False},
                )


            async def main() -> None:
                # Create the engine and database wrapper.
                engine = get_engine_for_chinook_db()
                db = SQLDatabase(engine)

                # Create the toolkit.
                llm = ChatOpenAI(temperature=0)
                toolkit = SQLDatabaseToolkit(db=db, llm=llm)

                # Create the LangChain tool adapter for every tool in the toolkit.
                tools = [LangChainToolAdapter(tool) for tool in toolkit.get_tools()]

                # Create the chat completion client.
                model_client = OpenAIChatCompletionClient(model="gpt-4o")

                # Create the assistant agent.
                agent = AssistantAgent(
                    "assistant",
                    model_client=model_client,
                    tools=tools,  # type: ignore
                    model_client_stream=True,
                    system_message="Respond with 'TERMINATE' if the task is completed.",
                )

                # Create termination condition.
                termination = TextMentionTermination("TERMINATE")

                # Create a round-robin group chat to iterate the single agent over multiple steps.
                chat = RoundRobinGroupChat([agent], termination_condition=termination)

                # Run the chat.
                await Console(chat.run_stream(task="Show some tables in the database"))


            if __name__ == "__main__":
                asyncio.run(main())

    """

    def __init__(self, langchain_tool: LangChainTool):
        self._langchain_tool: LangChainTool = langchain_tool

        # Extract name and description
        name = self._langchain_tool.name
        description = self._langchain_tool.description or ""

        # Determine the callable method
        if hasattr(self._langchain_tool, "func") and callable(self._langchain_tool.func):  # type: ignore
            assert self._langchain_tool.func is not None  # type: ignore
            self._callable: Callable[..., Any] = self._langchain_tool.func  # type: ignore
        elif hasattr(self._langchain_tool, "_run") and callable(self._langchain_tool._run):  # type: ignore
            self._callable: Callable[..., Any] = self._langchain_tool._run  # type: ignore
        else:
            raise AttributeError(
                f"The provided LangChain tool '{name}' does not have a callable 'func' or '_run' method."
            )

        # Determine args_type
        if self._langchain_tool.args_schema:  # pyright: ignore
            args_type = self._langchain_tool.args_schema  # pyright: ignore
        else:
            # Infer args_type from the callable's signature
            sig = inspect.signature(cast(Callable[..., Any], self._callable))  # type: ignore
            fields = {
                k: (v.annotation, Field(...))
                for k, v in sig.parameters.items()
                if k != "self"
                and v.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
                and k != "run_manager"  # Exclude LangChain callback manager parameters
            }
            args_type = create_model(f"{name}Args", **fields)  # type: ignore
            # Note: type ignore is used due to a LangChain typing limitation

        # Ensure args_type is a subclass of BaseModel
        if not issubclass(args_type, BaseModel):
            raise ValueError(f"Failed to create a valid Pydantic v2 model for {name}")

        # Assume return_type as Any if not specified
        return_type: Type[Any] = object

        super().__init__(args_type, return_type, name, description)

    async def run(self, args: BaseModel, cancellation_token: CancellationToken) -> Any:
        # Prepare arguments
        kwargs = args.model_dump()

        # Determine if the callable is asynchronous
        if inspect.iscoroutinefunction(self._callable):
            return await self._callable(**kwargs)
        else:
            # Run in a thread to avoid blocking the event loop
            return await asyncio.to_thread(self._call_sync, kwargs)

    def _call_sync(self, kwargs: Dict[str, Any]) -> Any:
        return self._callable(**kwargs)
