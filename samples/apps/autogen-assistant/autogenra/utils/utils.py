import ast
import base64
import hashlib
from typing import List, Dict, Tuple, Union
import os
import shutil
import re
import autogen
from ..datamodel import AgentConfig, AgentFlowSpec, AgentWorkFlowConfig, LLMConfig


def md5_hash(text: str) -> str:
    """
    Compute the MD5 hash of a given text.

    :param text: The string to hash
    :return: The MD5 hash of the text
    """
    return hashlib.md5(text.encode()).hexdigest()


def get_file_type(file_path: str) -> str:
    """


    Get file type   determined by the file extension. If the file extension is not
    recognized, 'unknown' will be used as the file type.

    :param file_path: The path to the file to be serialized.
    :return: A  string containing the file type.
    """

    # Extended list of file extensions for code and text files
    CODE_EXTENSIONS = {
        ".py",
        ".js",
        ".jsx",
        ".java",
        ".c",
        ".cpp",
        ".cs",
        ".ts",
        ".tsx",
        ".html",
        ".css",
        ".scss",
        ".less",
        ".json",
        ".xml",
        ".yaml",
        ".yml",
        ".md",
        ".rst",
        ".tex",
        ".sh",
        ".bat",
        ".ps1",
        ".php",
        ".rb",
        ".go",
        ".swift",
        ".kt",
        ".hs",
        ".scala",
        ".lua",
        ".pl",
        ".sql",
        ".config",
    }

    # Supported image extensions
    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".svg", ".webp"}

    # Supported PDF extension
    PDF_EXTENSION = ".pdf"

    # Determine the file extension
    _, file_extension = os.path.splitext(file_path)

    # Determine the file type based on the extension
    if file_extension in CODE_EXTENSIONS:
        file_type = "code"
    elif file_extension in IMAGE_EXTENSIONS:
        file_type = "image"
    elif file_extension == PDF_EXTENSION:
        file_type = "pdf"
    else:
        file_type = "unknown"

    return file_type


def serialize_file(file_path: str) -> Tuple[str, str]:
    """
    Reads a file from a given file path, base64 encodes its content,
    and returns the base64 encoded string along with the file type.

    The file type is determined by the file extension. If the file extension is not
    recognized, 'unknown' will be used as the file type.

    :param file_path: The path to the file to be serialized.
    :return: A tuple containing the base64 encoded string of the file and the file type.
    """

    file_type = get_file_type(file_path)

    # Read the file and encode its contents
    try:
        with open(file_path, "rb") as file:
            file_content = file.read()
            base64_encoded_content = base64.b64encode(file_content).decode("utf-8")
    except Exception as e:
        raise IOError(f"An error occurred while reading the file: {e}")

    return base64_encoded_content, file_type


def get_modified_files(
    start_timestamp: float, end_timestamp: float, source_dir: str, dest_dir: str
) -> List[Dict[str, str]]:
    """
    Copy files from source_dir that were modified within a specified timestamp range
    to dest_dir, renaming files if they already exist there. The function excludes
    files with certain file extensions and names.

    :param start_timestamp: The start timestamp to filter modified files.
    :param end_timestamp: The end timestamp to filter modified files.
    :param source_dir: The directory to search for modified files.
    :param dest_dir: The destination directory to copy modified files to.

    :return: A list of dictionaries with details of file paths in dest_dir that were modified and copied over.
             Dictionary format: {path: "", name: "", extension: ""}
             Files with extensions "__pycache__", "*.pyc", "__init__.py", and "*.cache"
             are ignored.
    """
    modified_files = []
    ignore_extensions = {".pyc", ".cache"}
    ignore_files = {"__pycache__", "__init__.py"}

    for root, dirs, files in os.walk(source_dir):
        # Excluding the directory "__pycache__" if present
        dirs[:] = [d for d in dirs if d not in ignore_files]

        for file in files:
            file_path = os.path.join(root, file)
            file_ext = os.path.splitext(file)[1]
            file_name = os.path.basename(file)

            if file_ext in ignore_extensions or file_name in ignore_files:
                continue

            file_mtime = os.path.getmtime(file_path)
            if start_timestamp < file_mtime < end_timestamp:
                dest_file_path = os.path.join(dest_dir, file)
                copy_idx = 1
                while os.path.exists(dest_file_path):
                    base, extension = os.path.splitext(file)
                    # Handling potential name conflicts by appending a number
                    dest_file_path = os.path.join(dest_dir, f"{base}_{copy_idx}{extension}")
                    copy_idx += 1

                # Copying the modified file to the destination directory
                shutil.copy2(file_path, dest_file_path)

                # Extract user id from the dest_dir and file path
                uid = dest_dir.split("/")[-1]
                relative_file_path = os.path.relpath(dest_file_path, start=dest_dir)
                file_type = get_file_type(dest_file_path)
                file_dict = {
                    "path": f"files/user/{uid}/{relative_file_path}",
                    "name": file_name,
                    "extension": file_ext.replace(".", ""),
                    "type": file_type,
                }
                modified_files.append(file_dict)
    # sort by extension
    modified_files.sort(key=lambda x: x["extension"])
    return modified_files


def init_webserver_folders(root_file_path: str) -> Dict[str, str]:
    """
    Initialize folders needed for a web server, such as static file directories
    and user-specific data directories.

    :param root_file_path: The root directory where webserver folders will be created
    :return: A dictionary with the path of each created folder
    """
    files_static_root = os.path.join(root_file_path, "files/")
    static_folder_root = os.path.join(root_file_path, "ui")
    workdir_root = os.path.join(root_file_path, "workdir")
    skills_dir = os.path.join(root_file_path, "skills")
    user_skills_dir = os.path.join(skills_dir, "user")
    global_skills_dir = os.path.join(skills_dir, "global")

    os.makedirs(files_static_root, exist_ok=True)
    os.makedirs(os.path.join(files_static_root, "user"), exist_ok=True)
    os.makedirs(static_folder_root, exist_ok=True)
    os.makedirs(workdir_root, exist_ok=True)
    os.makedirs(skills_dir, exist_ok=True)
    os.makedirs(user_skills_dir, exist_ok=True)
    os.makedirs(global_skills_dir, exist_ok=True)

    folders = {
        "files_static_root": files_static_root,
        "static_folder_root": static_folder_root,
        "workdir_root": workdir_root,
        "skills_dir": skills_dir,
        "user_skills_dir": user_skills_dir,
        "global_skills_dir": global_skills_dir,
    }
    return folders


def skill_from_folder(folder: str) -> List[Dict[str, str]]:
    """
    Given a folder, return a dict of the skill (name, python file content). Only python files are considered.

    :param folder: The folder to search for skills
    :return: A list of dictionaries, each representing a skill
    """

    skills = []
    for root, dirs, files in os.walk(folder):
        for file in files:
            if file.endswith(".py"):
                skill_name = file.split(".")[0]
                skill_file_path = os.path.join(root, file)
                with open(skill_file_path, "r", encoding="utf-8") as f:
                    skill_content = f.read()
                skills.append({"name": skill_name, "content": skill_content, "file_name": file})
    return skills


def get_all_skills(user_skills_path: str, global_skills_path: str, dest_dir: str = None) -> List[Dict[str, str]]:
    """
    Get all skills from the user and global skills directories. If dest_dir, copy all skills to dest_dir.

    :param user_skills_path: The path to the user skills directory
    :param global_skills_path: The path to the global skills directory
    :param dest_dir: The destination directory to copy all skills to
    :return: A dictionary of user and global skills
    """
    user_skills = skill_from_folder(user_skills_path)
    os.makedirs(user_skills_path, exist_ok=True)
    global_skills = skill_from_folder(global_skills_path)
    skills = {
        "user": user_skills,
        "global": global_skills,
    }

    if dest_dir:
        # chcek if dest_dir exists
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        # copy all skills to dest_dir
        for skill in user_skills + global_skills:
            skill_file_path = os.path.join(dest_dir, skill["file_name"])
            with open(skill_file_path, "w", encoding="utf-8") as f:
                f.write(skill["content"])

    return skills


def get_skills_prompt(skills: List[Dict[str, str]]) -> str:
    """
    Get a prompt with the content of all skills.

    :param skills: A dictionary of user and global skills
    :return: A string containing the content of all skills
    """
    user_skills = skills["user"]
    global_skills = skills["global"]
    all_skills = user_skills + global_skills

    prompt = """

While solving the task you may use functions in the files below.
To use a function from a file in code, import the file and then use the function.
If you need to install python packages, write shell code to
install via pip and use --quiet option.

         """
    for skill in all_skills:
        prompt += f"""

##### Begin of {skill["file_name"]} #####

{skill["content"]}

#### End of {skill["file_name"]} ####

        """

    return prompt


def delete_files_in_folder(folders: Union[str, List[str]]) -> None:
    """
    Delete all files and directories in the specified folders.

    :param folders: A list of folders or a single folder string
    """

    if isinstance(folders, str):
        folders = [folders]

    for folder in folders:
        # Check if the folder exists
        if not os.path.isdir(folder):
            print(f"The folder {folder} does not exist.")
            continue

        # List all the entries in the directory
        for entry in os.listdir(folder):
            # Get the full path
            path = os.path.join(folder, entry)
            try:
                if os.path.isfile(path) or os.path.islink(path):
                    # Remove the file or link
                    os.remove(path)
                elif os.path.isdir(path):
                    # Remove the directory and all its content
                    shutil.rmtree(path)
            except Exception as e:
                # Print the error message and skip
                print(f"Failed to delete {path}. Reason: {e}")


def get_default_agent_config(work_dir: str, skills_suffix: str = "") -> AgentWorkFlowConfig:
    """
    Get a default agent flow config .
    """

    llm_config = LLMConfig(
        config_list=[{"model": "gpt-4"}],
        temperature=0,
    )

    USER_PROXY_INSTRUCTIONS = """If the request has been addressed sufficiently, summarize the answer and end with the word TERMINATE. Otherwise, ask a follow-up question.
        """

    userproxy_spec = AgentFlowSpec(
        type="userproxy",
        config=AgentConfig(
            name="user_proxy",
            human_input_mode="NEVER",
            system_message=USER_PROXY_INSTRUCTIONS,
            code_execution_config={
                "work_dir": work_dir,
                "use_docker": False,
            },
            max_consecutive_auto_reply=10,
            llm_config=llm_config,
            is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
        ),
    )

    assistant_spec = AgentFlowSpec(
        type="assistant",
        config=AgentConfig(
            name="primary_assistant",
            system_message=autogen.AssistantAgent.DEFAULT_SYSTEM_MESSAGE + skills_suffix,
            llm_config=llm_config,
        ),
    )

    flow_config = AgentWorkFlowConfig(
        name="default",
        sender=userproxy_spec,
        receiver=assistant_spec,
        type="default",
    )

    return flow_config


def extract_successful_code_blocks(messages: List[Dict[str, str]]) -> List[str]:
    """
    Parses through a list of messages containing code blocks and execution statuses,
    returning the array of code blocks that executed successfully and retains
    the backticks for Markdown rendering.

    Parameters:
    messages (List[Dict[str, str]]): A list of message dictionaries containing 'content' and 'role' keys.

    Returns:
    List[str]: A list containing the code blocks that were successfully executed, including backticks.
    """
    successful_code_blocks = []
    code_block_regex = r"```[\s\S]*?```"  # Regex pattern to capture code blocks enclosed in triple backticks.

    for i, message in enumerate(messages):
        if message["role"] == "user" and "execution succeeded" in message["content"]:
            if i > 0 and messages[i - 1]["role"] == "assistant":
                prev_content = messages[i - 1]["content"]
                # Find all matches for code blocks
                code_blocks = re.findall(code_block_regex, prev_content)
                successful_code_blocks.extend(code_blocks)  # Add the code blocks with backticks

    return successful_code_blocks


def create_skills_from_code(dest_dir: str, skills: Union[str, List[str]]) -> None:
    """
    Create skills from a list of code blocks.
    Parameters:
    dest_dir (str): The destination directory to copy all skills to.
    skills (Union[str, List[str]]): A list of strings containing code blocks.
    """

    # Ensure skills is a list
    if isinstance(skills, str):
        skills = [skills]

    # Check if dest_dir exists
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    for skill in skills:
        # Attempt to parse the code and extract the top-level function name
        try:
            parsed = ast.parse(skill)
            function_name = None
            for node in parsed.body:
                if isinstance(node, ast.FunctionDef):
                    function_name = node.name
                    break

            if function_name is None:
                raise ValueError("No top-level function definition found.")

            # Sanitize the function name for use as a file name
            function_name = "".join(ch for ch in function_name if ch.isalnum() or ch == "_")
            skill_file_name = f"{function_name}.py"

        except (ValueError, SyntaxError):
            skill_file_name = "new_skill.py"

        # If the generated/sanitized name already exists, append an index
        skill_file_path = os.path.join(dest_dir, skill_file_name)
        index = 1
        while os.path.exists(skill_file_path):
            base, ext = os.path.splitext(skill_file_name)
            if base.endswith(f"_{index - 1}"):
                base = base.rsplit("_", 1)[0]

            skill_file_path = os.path.join(dest_dir, f"{base}_{index}{ext}")
            index += 1

        # Write the skill to the file
        with open(skill_file_path, "w", encoding="utf-8") as f:
            f.write(skill)
