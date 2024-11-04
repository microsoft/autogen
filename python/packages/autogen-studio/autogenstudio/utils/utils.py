import base64
import hashlib
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

from dotenv import load_dotenv
from loguru import logger


from ..datamodel import Model
from ..version import APP_NAME


def sha256_hash(text: str) -> str:
    """
    Compute the MD5 hash of a given text.

    :param text: The string to hash
    :return: The MD5 hash of the text
    """
    return hashlib.sha256(text.encode()).hexdigest()


def check_and_cast_datetime_fields(obj: Any) -> Any:
    if hasattr(obj, "created_at") and isinstance(obj.created_at, str):
        obj.created_at = str_to_datetime(obj.created_at)

    if hasattr(obj, "updated_at") and isinstance(obj.updated_at, str):
        obj.updated_at = str_to_datetime(obj.updated_at)

    return obj


def str_to_datetime(dt_str: str) -> datetime:
    if dt_str[-1] == "Z":
        # Replace 'Z' with '+00:00' for UTC timezone
        dt_str = dt_str[:-1] + "+00:00"
    return datetime.fromisoformat(dt_str)


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

    # Supported spreadsheet extensions
    CSV_EXTENSIONS = {".csv", ".xlsx"}

    # Supported image extensions
    IMAGE_EXTENSIONS = {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".tiff",
        ".svg",
        ".webp",
    }
    # Supported (web) video extensions
    VIDEO_EXTENSIONS = {".mp4", ".webm", ".ogg", ".mov", ".avi", ".wmv"}

    # Supported PDF extension
    PDF_EXTENSION = ".pdf"

    # Determine the file extension
    _, file_extension = os.path.splitext(file_path)

    # Determine the file type based on the extension
    if file_extension in CODE_EXTENSIONS:
        file_type = "code"
    elif file_extension in CSV_EXTENSIONS:
        file_type = "csv"
    elif file_extension in IMAGE_EXTENSIONS:
        file_type = "image"
    elif file_extension == PDF_EXTENSION:
        file_type = "pdf"
    elif file_extension in VIDEO_EXTENSIONS:
        file_type = "video"
    else:
        file_type = "unknown"

    return file_type


def get_modified_files(start_timestamp: float, end_timestamp: float, source_dir: str) -> List[Dict[str, str]]:
    """
    Identify files from source_dir that were modified within a specified timestamp range.
    The function excludes files with certain file extensions and names.

    :param start_timestamp: The floating-point number representing the start timestamp to filter modified files.
    :param end_timestamp: The floating-point number representing the end timestamp to filter modified files.
    :param source_dir: The directory to search for modified files.

    :return: A list of dictionaries with details of relative file paths that were modified.
             Dictionary format: {path: "", name: "", extension: "", type: ""}
             Files with extensions "__pycache__", "*.pyc", "__init__.py", and "*.cache"
             are ignored.
    """
    modified_files = []
    ignore_extensions = {".pyc", ".cache"}
    ignore_files = {"__pycache__", "__init__.py"}

    # Walk through the directory tree
    for root, dirs, files in os.walk(source_dir):
        # Update directories and files to exclude those to be ignored
        dirs[:] = [d for d in dirs if d not in ignore_files]
        files[:] = [f for f in files if f not in ignore_files and os.path.splitext(f)[
            1] not in ignore_extensions]

        for file in files:
            file_path = os.path.join(root, file)
            file_mtime = os.path.getmtime(file_path)

            # Verify if the file was modified within the given timestamp range
            if start_timestamp <= file_mtime <= end_timestamp:
                file_relative_path = (
                    "files/user" +
                    file_path.split(
                        "files/user", 1)[1] if "files/user" in file_path else ""
                )
                file_type = get_file_type(file_path)

                file_dict = {
                    "path": file_relative_path,
                    "name": os.path.basename(file),
                    # Remove the dot
                    "extension": os.path.splitext(file)[1].lstrip("."),
                    "type": file_type,
                }
                modified_files.append(file_dict)

    # Sort the modified files by extension
    modified_files.sort(key=lambda x: x["extension"])
    return modified_files


def get_app_root() -> str:
    """
    Get the root directory of the application.

    :return: The root directory of the application.
    """
    app_name = f".{APP_NAME}"
    default_app_root = os.path.join(os.path.expanduser("~"), app_name)
    if not os.path.exists(default_app_root):
        os.makedirs(default_app_root, exist_ok=True)
    app_root = os.environ.get("AUTOGENSTUDIO_APPDIR") or default_app_root
    return app_root


def get_db_uri(app_root: str) -> str:
    """
    Get the default database URI for the application.

    :param app_root: The root directory of the application.
    :return: The default database URI.
    """
    db_uri = f"sqlite:///{os.path.join(app_root, 'database.sqlite')}"
    db_uri = os.environ.get("AUTOGENSTUDIO_DATABASE_URI") or db_uri
    logger.info(f"Using database URI: {db_uri}")
    return db_uri


def init_app_folders(app_file_path: str) -> Dict[str, str]:
    """
    Initialize folders needed for a web server, such as static file directories
    and user-specific data directories. Also load any .env file if it exists.

    :param root_file_path: The root directory where webserver folders will be created
    :return: A dictionary with the path of each created folder
    """
    app_root = get_app_root()

    if not os.path.exists(app_root):
        os.makedirs(app_root, exist_ok=True)

    # load .env file if it exists
    env_file = os.path.join(app_root, ".env")
    if os.path.exists(env_file):
        logger.info(f"Loaded environment variables from {env_file}")
        load_dotenv(env_file)

    files_static_root = os.path.join(app_root, "files/")
    static_folder_root = os.path.join(app_file_path, "ui")

    os.makedirs(files_static_root, exist_ok=True)
    os.makedirs(os.path.join(files_static_root, "user"), exist_ok=True)
    os.makedirs(static_folder_root, exist_ok=True)
    folders = {
        "files_static_root": files_static_root,
        "static_folder_root": static_folder_root,
        "app_root": app_root,
        "database_engine_uri": get_db_uri(app_root=app_root),
    }
    logger.info(f"Initialized application data folder: {app_root}")
    return folders


def sanitize_model(model: Model):
    """
    Sanitize model dictionary to remove None values and empty strings and only keep valid keys.
    """
    if isinstance(model, Model):
        model = model.model_dump()
    valid_keys = ["model", "base_url", "api_key", "api_type", "api_version"]
    # only add key if value is not None
    sanitized_model = {k: v for k, v in model.items() if (
        v is not None and v != "") and k in valid_keys}
    return sanitized_model


def test_model(model: Model):
    """
    Test the model endpoint by sending a simple message to the model and returning the response.
    """

    print("Testing model", model)


# def summarize_chat_history(task: str, messages: List[Dict[str, str]], client: ModelClient):
#     """
#     Summarize the chat history using the model endpoint and returning the response.
#     """
#     summarization_system_prompt = f"""
#     You are a helpful assistant that is able to review the chat history between a set of agents (userproxy agents, assistants etc) as they try to address a given TASK and provide a summary. Be SUCCINCT but also comprehensive enough to allow others (who cannot see the chat history) understand and recreate the solution.

#     The task requested by the user is:
#     ===
#     {task}
#     ===
#     The summary should focus on extracting the actual solution to the task from the chat history (assuming the task was addressed) such that any other agent reading the summary will understand what the actual solution is. Use a neutral tone and DO NOT directly mention the agents. Instead only focus on the actions that were carried out (e.g. do not say 'assistant agent generated some code visualization code ..'  instead say say 'visualization code was generated ..'. The answer should be framed as a response to the user task. E.g. if the task is "What is the height of the Eiffel tower", the summary should be "The height of the Eiffel Tower is ...").
#     """
#     summarization_prompt = [
#         {
#             "role": "system",
#             "content": summarization_system_prompt,
#         },
#         {
#             "role": "user",
#             "content": f"Summarize the following chat history. {str(messages)}",
#         },
#     ]
#     response = client.create(messages=summarization_prompt, cache_seed=None)
#     return response.choices[0].message.content
