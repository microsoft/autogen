import importlib.util
import inspect
import os
from textwrap import dedent, indent


def get_full_tool_description(py_file):
    """
    Retrieves the function signature for a given Python file.
    """
    with open(py_file, "r") as f:
        code = f.read()
        exec(code)
        function_name = os.path.splitext(os.path.basename(py_file))[0]
        if function_name in locals():
            func = locals()[function_name]
            content = f"def {func.__name__}{inspect.signature(func)}:\n"
            docstring = func.__doc__

            if docstring:
                docstring = dedent(docstring)
                docstring = '"""' + docstring + '"""'
                docstring = indent(docstring, "    ")
                content += docstring + "\n"
            return content
        else:
            raise ValueError(f"Function {function_name} not found in {py_file}")


def find_callables(directory):
    """
    Find all callable objects defined in Python files within the specified directory.
    """
    callables = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                module_name = os.path.splitext(file)[0]
                module_path = os.path.join(root, file)
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                for name, value in module.__dict__.items():
                    if callable(value) and name == module_name:
                        callables.append(value)
                        break
    return callables
