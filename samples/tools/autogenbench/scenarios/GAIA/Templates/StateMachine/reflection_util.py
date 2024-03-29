from datetime import datetime
import functools
import types
import autogen
import copy
import inspect
from typing import Dict, List


class ReflectionUtil:
    @staticmethod
    def wrap_method(method, detailed=False, name=None, arg_names: List[str] = None, tag: str = None):
        @functools.wraps(method)
        def wrapper(*args, **kwargs):
            if detailed:
                if arg_names is None:
                    to_print = kwargs
                else:
                    to_print = {k: kwargs[k] for k in arg_names if k in kwargs}
                print(
                    f"%%% {datetime.now()} {tag} {name} [enter] Calling {method.__module__}.{method.__name__} with args {args} and kwargs {to_print}"
                )
            else:
                print(
                    f"%%% {datetime.now()} {tag} {name} [enter] Calling {method.__module__}.{method.__name__} with args:count {len(args)} and kwargs:count {len(kwargs)}"
                )

            result = method(*args, **kwargs)
            print(
                f"%%% {datetime.now()} {tag} {name} [return] Returning from {method.__module__}.{method.__name__} with result {result}"
            )
            return result

        return wrapper

    @staticmethod
    def awrap_method(method, detailed=False, arg_names: List[str] = None, name=None, tag: str = None):
        @functools.wraps(method)
        async def wrapper(*args, **kwargs):
            if detailed:
                if arg_names is None:
                    to_print = kwargs
                else:
                    to_print = {k: kwargs[k] for k in arg_names if k in kwargs}
                print(
                    f"%%% {datetime.now()} {tag} {name} [enter] Calling async {method.__module__}.{method.__name__} with args {args} and kwargs {to_print}"
                )
            else:
                print(
                    f"%%% {datetime.now()} {tag} {name} [enter] Calling async {method.__module__}.{method.__name__} with args:count {len(args)} and kwargs:count {len(kwargs)}"
                )

            result = await method(*args, **kwargs)
            print(
                f"%%% {datetime.now()} {tag} {name} [return] Returning from async {method.__module__}.{method.__name__} with result {result}"
            )
            return result

        return wrapper

    @staticmethod
    def wrap_reply_funcs(agent: autogen.ConversableAgent):
        if hasattr(agent, "_reply_func_list"):
            for i in range(len(agent._reply_func_list)):
                if not inspect.iscoroutinefunction(agent._reply_func_list[i]["reply_func"]):
                    agent._reply_func_list[i]["reply_func"] = ReflectionUtil.wrap_method(
                        agent._reply_func_list[i]["reply_func"], detailed=False, name=agent.name, tag="[reply_func]"
                    )
                else:
                    agent._reply_func_list[i]["reply_func"] = ReflectionUtil.awrap_method(
                        agent._reply_func_list[i]["reply_func"], detailed=False, name=agent.name, tag="[reply_func]"
                    )

    @staticmethod
    def add_tracing_to_class(cls, detailed: Dict[str, List[str]] = {}):
        """Dynamically add tracing to all methods of a class."""
        banned = []

        # Iterate over all attributes of the class
        for attr_name, attr_value in cls.__dict__.items():
            if attr_name in banned:
                continue

            if isinstance(attr_value, (types.FunctionType, types.MethodType)):
                # Wrap the method with the logging wrapper
                setattr(
                    cls,
                    attr_name,
                    ReflectionUtil.wrap_method(
                        attr_value,
                        attr_name in detailed,
                        arg_names=detailed.get(attr_name, []),
                        name=cls.__name__,
                        tag="[method]",
                    ),
                )
            elif isinstance(attr_value, classmethod):
                # Handle classmethod
                original_method = attr_value.__func__
                setattr(
                    cls,
                    attr_name,
                    classmethod(
                        ReflectionUtil.wrap_method(
                            original_method,
                            attr_name in detailed,
                            arg_names=detailed.get(attr_name, []),
                            name=cls.__name__,
                            tag="[classmethod]",
                        )
                    ),
                )
            elif isinstance(attr_value, staticmethod):
                # Handle staticmethod
                original_method = attr_value.__func__
                setattr(
                    cls,
                    attr_name,
                    staticmethod(
                        ReflectionUtil.wrap_method(
                            original_method,
                            attr_name in detailed,
                            arg_names=detailed.get(attr_name, []),
                            name=cls.__name__,
                            tag="[staticmethod]",
                        )
                    ),
                )

        return cls

    @staticmethod
    def replace_conversable_agent_properties(obj):
        # Iterate through all properties of the object
        for attr_name in dir(obj):
            # Ignore special properties
            if attr_name.startswith("__") and attr_name.endswith("__"):
                continue

            # Get the attribute's value
            attr_value = getattr(obj, attr_name)

            # Check if the attribute is an instance of ConversableAgent or its subclasses
            if isinstance(attr_value, autogen.ConversableAgent):
                # Replace the attribute with its copy
                # setattr(obj, attr_name, copy.copy(attr_value))
                ReflectionUtil.wrap_reply_funcs(attr_value)
                print(attr_name)

            # Additionally, if you want to recursively replace ConversableAgent instances in nested objects
            elif hasattr(attr_value, "__dict__") or isinstance(attr_value, (list, dict)):
                # If it's a dictionary, iterate through its values
                if isinstance(attr_value, dict):
                    for key in list(attr_value.keys()):
                        value = attr_value[key]
                        if isinstance(value, autogen.ConversableAgent):
                            attr_value[key] = copy.copy(value)
                        elif hasattr(value, "__dict__") or isinstance(value, (list, dict)):
                            # replace_conversable_agent_properties(value)
                            continue
                # If it's a list, iterate through its elements
                elif isinstance(attr_value, list):
                    for i in range(len(attr_value)):
                        value = attr_value[i]
                        if isinstance(value, autogen.ConversableAgent):
                            attr_value[i] = copy.copy(value)
                        elif hasattr(value, "__dict__") or isinstance(value, (list, dict)):
                            # replace_conversable_agent_properties(value)
                            continue
                # if its callable, ignore
                elif callable(attr_value):
                    continue
                # Otherwise, handle as a single object
                else:
                    # replace_conversable_agent_properties(attr_value)
                    continue
