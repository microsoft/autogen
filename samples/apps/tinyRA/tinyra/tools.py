import ast
from typing import Optional
from dataclasses import dataclass

from .exceptions import InvalidToolError


@dataclass
class Tool:
    """
    Represents a tool in the system.
    """

    id: Optional[int] = None
    name: str = ""
    code: Optional[str] = ""
    description: Optional[str] = ""

    def validate_tool(self):
        # validate the name
        min_tool_name_length = 6
        if len(self.name) < min_tool_name_length:
            raise InvalidToolError(f"Tool name must be at least {min_tool_name_length} characters long")

        # check if self.code contains valid python code
        try:
            module = ast.parse(self.code)
            if not isinstance(module, ast.Module):
                raise InvalidToolError("Code must be a valid python module")
        except SyntaxError as e:
            raise InvalidToolError(f"Code must not contain syntax errors. Current errors:\n{e}")

        # validate the description
        if len(self.code) > 0 and not self.description:
            module = ast.parse(self.code)
            if module.body and isinstance(module.body[0], (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_def = module.body[0]
                docstring = ast.get_docstring(function_def)
                if not docstring:
                    raise InvalidToolError("Code must contain a doc string")
                else:
                    self.description = docstring
            else:
                raise InvalidToolError("Code must contain a valid (sync/async) function definition")

        return True
