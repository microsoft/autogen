from typing import Any, Callable, Dict, List, Literal, Optional, Union
from pydantic.dataclasses import dataclass
from dataclasses import asdict, field
import inspect


@dataclass
class Skill:
    """
    A skill is a self-contained, valid python function.

    It contains a title, a description, and the content of the skill.

    For example, the following python function is a valid skill:

        ```python
        def add(a, b):
            "Adds two numbers."
            return a + b
        ```
    The corresponding Skill object would be:

            ```python
            Skill(
                title="Addition skill",
                description="Adds two numbers.",
                content="def add(a, b):\n    return a + b"
            )
            ```
    """

    title: str
    content: str
    description: Optional[str] = None

    def dict(self):
        """
        Returns a dictionary representation of the Skill object.
        """
        result = asdict(self)
        return result


def function_to_skill(foo: callable) -> Skill:
    """
    Converts a python function to a Skill object.

    Args:
        foo (callable): a python function.

    Returns:
        Skill: a Skill object.
    """
    return Skill(title=foo.__name__, content=inspect.getsource(foo), description=foo.__doc__)


def skills_to_prompt(skills: List[Skill]) -> str:
    """
    Create a prompt with the content of all skills.

    Args:
        skills (list[Skill]): a list of skills.

    Returns:
        str: a prompt with the content of all skills that can be appended to the system message.
    """

    skill_prompt = """
While solving the task you may use the functions are available in a python module called "skills".
To use a function from "skills" in code, IMPORT THE FUNCTION FROM the skills module and use it.
For example, to use the "add" function from the skills module, you need to import it first:

```python
from skills import add
```

Then you can use it in your code:

```python
a = 1
b = 2
c = add(a, b)
```

"""
    for skill in skills:
        skill_prompt += f"""

##### Begin of {skill.title} #####

{skill.content}

#### End of {skill.title} ####

    """
    return skill_prompt


def skills_to_module(skills: List[Skill], filename) -> str:
    """
    Create a module with the content of all skills.

    Args:
        skills (list[Skill]): a list of skills.

    Returns:
        str: a module with the content of all skills.
    """
    skill_module = ""
    for skill in skills:
        skill_module += skill.content + "\n\n"

    with open(filename, "w") as f:
        f.write(skill_module)
