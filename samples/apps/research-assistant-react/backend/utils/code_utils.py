from typing import List
import json
import os
import ast
from datetime import datetime

from autogen.code_utils import extract_code

from utils import get_standalone_func

# pylint: disable=no-name-in-module
from pydantic import BaseModel


def extract_code_result(messages):
    N = len(messages)
    for i in range(N):
        msg = messages[N - i - 1]
        role = msg["role"]
        content = msg["content"]

        if role == "user" and content.startswith("exitcode:"):
            result = content
            # result = "\n".join(result.split("\n")[2:])
            code = extract_code(messages[N - i - 2]["content"])
            code = "\n".join([c[1] for c in code])
            return code, result

    return None, "There were no codes or results..."


def utils_2_skills(utils_dir):
    """
    Parse all python files in the utils_dir and return a list of skills.
    """
    skills = []
    for dir in utils_dir:
        if not os.path.exists(dir):
            os.makedirs(dir, exist_ok=True)
        # list all python files in dir
        python_files = os.listdir(dir)
        python_files = [os.path.join(dir, file) for file in python_files if file.endswith(".py")]
        for f in python_files:
            skills.append(
                {
                    "file_name": f,
                    "functions": python2functions(f),
                }
            )
    return skills


def _loop_dir(dirpath):
    prompt_suffix = ""
    utils_text = ""
    for file in os.listdir(dirpath):
        if file.endswith(".py"):
            utils_text += python_utils_2_prompt(os.path.join(dirpath, file))

    prompt_suffix = f"""

While solving the task you may use functions in the files below.
To use a function from a file in code, import the file and then use the function.
If you need to install python packages, write shell code to
install via pip and use --quiet option.

{utils_text}

         """
    return prompt_suffix


def utils_2_prompt(utils_dir):
    # check if utils_dir is a single dir or a list of dirs
    if isinstance(utils_dir, list):
        prompt_suffix = ""
        for dirpath in utils_dir:
            prompt_suffix += _loop_dir(dirpath)
        return prompt_suffix
    elif isinstance(utils_dir, str):
        return _loop_dir(utils_dir)

    else:
        raise ValueError("utils_dir must be a list of dirs or a single dir")


class SkillFunction(BaseModel):
    source_file: str
    name: str
    args: List[str]
    docstring: str
    code: str
    timestamp_created: datetime
    timestamp_modified: datetime

    class Config:
        json_encoders = {
            # Convert datetime objects to ISO 8601 string format
            datetime: lambda dt: dt.isoformat(),
        }

    def to_json(self):
        return self.json()


# Set arbitrary_types_allowed to True in the model's configuration
SkillFunction.Config.arbitrary_types_allowed = True


def text2functions(content, source_file) -> List[SkillFunction]:
    tree = ast.parse(content)

    functions = []
    for item in tree.body:
        if isinstance(item, ast.FunctionDef):
            name = item.name
            args = [arg.arg for arg in item.args.args]
            docstring = ast.get_docstring(item) or "No docstring available"

            code = (
                content.splitlines()[item.lineno - 1 : item.end_lineno]
                if item.end_lineno
                else content.splitlines()[item.lineno - 1 :]
            )
            code = "\n".join(code)

            timestamp_created = datetime.now()
            timestamp_modified = datetime.now()

            skill_function = SkillFunction(
                source_file=source_file,
                name=name,
                args=args,
                docstring=docstring,
                code=code,
                timestamp_created=timestamp_created,
                timestamp_modified=timestamp_modified,
            )
            functions.append(skill_function)
    return functions


def python2functions(file_path) -> List[SkillFunction]:
    """
    Reads a python file and returns a list containing the functions in the file.

    Args:
        file_path (str): Path to the python file

    Returns:
        list: List of SkillFunction objects in the file
    """
    with open(file_path, "r") as f:
        content = f.read()

    functions = text2functions(content, file_path)
    return functions


def python_utils_2_prompt(python_file):
    with open(python_file, "r") as f:
        text = f.read()

    filename = os.path.basename(python_file)
    prompt_suffix = f"""

##### Begin of {filename} #####

{text}

#### End of {filename} ####

        """
    return prompt_suffix


def learn_skill(
    history,
    utils_dir,
    llm_config,
    learned_skill_source_file="learned_skills.py",
):
    """
    Utilizes the latest messages from the chat history to learn a new skill.
    The new skill will be inserted in the user's utils_dir.

    Args:
        user_id (str): The user id

    Returns:
        SkillFunction: The learned skill
    """
    last_assistant_message = None
    for msg in reversed(history):
        if msg["role"] == "assistant":
            last_assistant_message = msg
            break

    if last_assistant_message is not None and len(last_assistant_message) > 0:
        print("Last assistant message:{}\n".format(last_assistant_message))

    last_code = None
    if last_assistant_message is not None:
        metadata = json.loads(last_assistant_message["metadata"])
        last_code = metadata["code"]
        print("Last code:\n{}".format(last_code))

    if last_code is None:
        return {
            "role": "assistant",
            "content": "```\nNo code to learn from\n```",
            # Code should be none if there was no execution
            "code": None,
            "metadata": {
                "skill": None,
                "images": [],
                "scripts": [],
                "files": [],
            },
        }

    standalone_func = get_standalone_func(last_code, llm_config)
    code_blocks = extract_code(standalone_func)
    _, new_function = code_blocks[0]

    user_utils_dir = utils_dir
    if isinstance(utils_dir, list):
        user_utils_dir = utils_dir[-1]

    existing_skills = utils_2_skills(utils_dir)
    existing_skills_names = []
    for skill in existing_skills:
        for function in skill["functions"]:
            existing_skills_names.append(function.name)

    source_file = os.path.join(user_utils_dir, learned_skill_source_file)

    skill_function = text2functions(new_function, source_file)[0]

    print("Skill function", skill_function.name)

    version_counter = 1
    initial_name = skill_function.name
    while skill_function.name in existing_skills_names:
        print("The following name already exists:", skill_function.name)
        version_counter += 1
        skill_function.name = initial_name + f"_v{version_counter}"

    # in the code replace the old function name with the new function name
    skill_function.code = skill_function.code.replace(
        f"def {initial_name}",
        f"def {skill_function.name}",
    )

    # user_utils_dir = get_user_utils_dir(user_id)
    # file_path = os.path.join(user_utils_dir, source_file)
    with open(source_file, "a") as f:
        f.write("\n\n" + skill_function.code)

    return {
        "role": "assistant",
        "content": f"```\nLearned a new skill called `{skill_function.name}`\n```",
        # Code should be none if there was no execution
        "code": None,
        "metadata": {
            "skill": json.loads(skill_function.to_json()),
            "images": [],
            "scripts": [],
            "files": [],
        },
    }
