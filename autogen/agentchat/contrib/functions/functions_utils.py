import inspect
import functools
from typing import List, Optional
from typing_extensions import Protocol, runtime_checkable


@runtime_checkable
class UserDefinedFunction(Protocol):
    """
    Represents a user-defined function.

    Attributes:
        name (str): The name of the function.
        docstring (str): The documentation string of the function.
        code (str): The code of the function.
        python_packages (List[str]): The Python packages required by the function.
        secrets (List[str]): The secrets required by the function.
    """

    name: str
    docstring: str
    code: str
    python_packages: List[str]
    env_vars: List[str]

    def name(self) -> str:
        """Returns the name of the function."""
        return self.name

    def docstring(self) -> str:
        """Returns the documentation string of the function."""
        return self.docstring

    def code(self) -> str:
        """Returns the code of the function."""
        return self.code

    def python_packages(self) -> List[str]:
        """Returns the Python packages required by the function."""
        return self.python_packages

    def env_vars(self) -> List[str]:
        """Returns the environment variables required by the function."""
        return self.env_vars


class FunctionWithRequirements:
    """Decorator class that adds requirements and setup functionality to a function."""

    def __init__(self, python_packages: Optional[List[str]] = None, env_vars: Optional[List[str]] = None):
        self.python_packages = python_packages or []
        self.env_vars = env_vars or []

    def __call__(self, func: callable) -> UserDefinedFunction:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        wrapper.name = func.__name__  # The name of the function
        wrapper.docstring = func.__doc__
        wrapper.code = inspect.getsource(func)
        wrapper.python_packages = self.python_packages
        wrapper.env_vars = self.env_vars
        return wrapper


if __name__ == "__main__":

    @FunctionWithRequirements(python_packages=["youtube_transcript_api==0.6.0"])
    def my_function():
        """This is a sample function"""
        print("Hello world")

    print(my_function)
    print(my_function.name)
    print(my_function.docstring)
    print(my_function.code)
    print(my_function.python_packages)
    print(my_function.env_vars)

    print(isinstance(my_function, UserDefinedFunction))
