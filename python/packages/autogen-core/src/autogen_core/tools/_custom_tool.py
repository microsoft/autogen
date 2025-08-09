"""Example implementation of GPT-5 custom tools."""

from typing import Any

from .._component_config import ComponentBase
from ._base import BaseCustomTool, CustomToolFormat
from .. import CancellationToken


class CodeExecutorTool(BaseCustomTool[str]):
    """Example custom tool that executes Python code sent as freeform text."""
    
    def __init__(self) -> None:
        super().__init__(
            return_type=str,
            name="code_exec",
            description="Executes arbitrary Python code",
        )

    async def run(self, input_text: str, cancellation_token: CancellationToken) -> str:
        """Execute Python code from freeform text input.
        
        Args:
            input_text: Raw Python code as text
            cancellation_token: Cancellation token
            
        Returns:
            Execution result as string
        """
        # In a real implementation, you would execute the code in a secure sandbox
        # For this example, we'll just return a mock result
        return f"Executed code: {input_text[:100]}{'...' if len(input_text) > 100 else ''}"


class SQLQueryTool(BaseCustomTool[str]):
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
            """
        )
        
        super().__init__(
            return_type=str,
            name="sql_query", 
            description="Executes SQL queries with grammar constraints",
            format=sql_grammar,
        )

    async def run(self, input_text: str, cancellation_token: CancellationToken) -> str:
        """Execute SQL query from constrained text input.
        
        Args:
            input_text: SQL query text (constrained by grammar)
            cancellation_token: Cancellation token
            
        Returns:
            Query result as string
        """
        # In a real implementation, you would execute the SQL query
        return f"SQL Result: Executed query '{input_text}'"


class TimestampTool(BaseCustomTool[str]):
    """Example custom tool with regex grammar for timestamp validation."""
    
    def __init__(self) -> None:
        # Regex grammar for timestamp format
        timestamp_grammar = CustomToolFormat(
            type="grammar",
            syntax="regex",
            definition=r"^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01]) (?:[01]\d|2[0-3]):[0-5]\d$"
        )
        
        super().__init__(
            return_type=str,
            name="save_timestamp",
            description="Saves a timestamp in YYYY-MM-DD HH:MM format",
            format=timestamp_grammar,
        )

    async def run(self, input_text: str, cancellation_token: CancellationToken) -> str:
        """Save timestamp from regex-constrained input.
        
        Args:
            input_text: Timestamp string (constrained by regex)
            cancellation_token: Cancellation token
            
        Returns:
            Confirmation message
        """
        return f"Saved timestamp: {input_text}"