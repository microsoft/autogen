import ast
from typing import Optional


class InvalidToolError(Exception):
    pass


class Tool:
    def __init__(
        self, name: str, code: Optional[str] = None, description: Optional[str] = None, id: Optional[int] = None
    ):
        self.id = id
        self.name = name or ""
        self.code = code or ""
        self.description = description or ""

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

    @staticmethod
    def _extract_description_from_code(code: str) -> str:
        module = ast.parse(code)
        function_def = module.body[0]
        if not isinstance(function_def, (ast.FunctionDef, ast.AsyncFunctionDef)):
            raise InvalidToolError("Code must contain a valid (sync/async) function definition")

        docstring = ast.get_docstring(function_def)

        if not docstring:
            raise InvalidToolError("Code must contain a doc string")

        return docstring
