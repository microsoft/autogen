"""Example implementation of GPT-5 custom tools."""

from pydantic import BaseModel

from .. import CancellationToken
from ._base import BaseCustomTool, CustomToolFormat


class CodeResult(BaseModel):
    """Result from code execution."""

    output: str


class SQLResult(BaseModel):
    """Result from SQL query execution."""

    output: str


class TimestampResult(BaseModel):
    """Result from timestamp saving."""

    message: str


class CodeExecutorTool(BaseCustomTool[CodeResult]):
    """Example custom tool that executes Python code sent as freeform text."""

    def __init__(self) -> None:
        super().__init__(
            return_type=CodeResult,
            name="code_exec",
            description="Executes arbitrary Python code",
        )

    async def run(self, input_text: str, cancellation_token: CancellationToken) -> CodeResult:
        """Execute Python code from freeform text input.

        Args:
            input_text: Raw Python code as text
            cancellation_token: Cancellation token

        Returns:
            Execution result as CodeResult
        """
        # In a real implementation, you would execute the code in a secure sandbox
        # For this example, we'll just return a mock result
        return CodeResult(output=f"Executed code: {input_text[:100]}{'...' if len(input_text) > 100 else ''}")


class SQLQueryTool(BaseCustomTool[SQLResult]):
    """Example custom tool with grammar constraints for SQL queries."""

    def __init__(self) -> None:
        # Example Context-Free Grammar for basic SQL
        sql_grammar = CustomToolFormat(
            type="grammar",
            syntax="lark",
            definition="""
                start: select_statement
                select_statement: "SELECT" column_list "FROM" table_name "WHERE" condition ";"
                column_list: column ("," column)*
                column: IDENTIFIER
                table_name: IDENTIFIER
                condition: column ">" NUMBER

                IDENTIFIER: /[a-zA-Z_][a-zA-Z0-9_]*/
                NUMBER: /[0-9]+/

                %import common.WS
                %ignore WS
            """,
        )

        super().__init__(
            return_type=SQLResult,
            name="sql_query",
            description="Executes SQL queries with grammar constraints",
            format=sql_grammar,
        )

    async def run(self, input_text: str, cancellation_token: CancellationToken) -> SQLResult:
        """Execute SQL query from constrained text input.

        Args:
            input_text: SQL query text (constrained by grammar)
            cancellation_token: Cancellation token

        Returns:
            Query result as SQLResult
        """
        # In a real implementation, you would execute the SQL query
        return SQLResult(output=f"SQL Result: Executed query '{input_text}'")


class TimestampTool(BaseCustomTool[TimestampResult]):
    """Example custom tool with regex grammar for timestamp validation."""

    def __init__(self) -> None:
        # Regex grammar for timestamp format
        timestamp_grammar = CustomToolFormat(
            type="grammar",
            syntax="regex",
            definition=r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01]) (?:[01]\d|2[0-3]):[0-5]\d$",
        )

        super().__init__(
            return_type=TimestampResult,
            name="save_timestamp",
            description="Saves a timestamp in YYYY-MM-DD HH:MM format",
            format=timestamp_grammar,
        )

    async def run(self, input_text: str, cancellation_token: CancellationToken) -> TimestampResult:
        """Save timestamp from regex-constrained input.

        Args:
            input_text: Timestamp string (constrained by regex)
            cancellation_token: Cancellation token

        Returns:
            Confirmation message
        """
        return TimestampResult(message=f"Saved timestamp: {input_text}")
