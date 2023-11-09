import hashlib 
from .datamodel import Message 
from .db import DBManager 
import os
from shutil import copy2
from typing import List, Dict

def md5_hash(text: str) -> str:
    """
    Compute the MD5 hash of a given text.

    :param text: The string to hash
    :return: The MD5 hash of the text
    """
    return hashlib.md5(text.encode()).hexdigest()


def save_message(message: Message, dbmanager: DBManager) -> None:
    """
    Save a message in the database using the provided database manager.

    :param message: The Message object containing message data
    :param dbmanager: The DBManager instance used to interact with the database
    """
    query = "INSERT INTO messages (userId, rootMsgId, msgId, role, content, metadata, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)"
    args = (message.userId, message.rootMsgId, message.msgId, message.role, message.content, message.metadata, message.timestamp) 
    dbmanager.query(query=query, args=args)


def load_messages(user_id: str, dbmanager: DBManager) -> List[dict]:
    """
    Load messages for a specific user from the database, sorted by timestamp.

    :param user_id: The ID of the user whose messages are to be loaded
    :param dbmanager: The DBManager instance to interact with the database
    :return: A list of dictionaries, each representing a message
    """
    query = "SELECT * FROM messages WHERE userId = ?"
    args = (user_id,)
    result = dbmanager.query(query=query, args=args, json=True)
    # Sort by timestamp ascending
    result = sorted(result, key=lambda k: k["timestamp"], reverse=False)
    return result


def delete_message(user_id: str, msg_id: str, dbmanager: DBManager, delete_all: bool = False) -> List[dict]:
    """
    Delete a specific message or all messages for a user from the database.

    :param user_id: The ID of the user whose messages are to be deleted
    :param msg_id: The ID of the specific message to be deleted (ignored if delete_all is True)
    :param dbmanager: The DBManager instance to interact with the database
    :param delete_all: If True, all messages for the user will be deleted
    :return: A list of the remaining messages if not all were deleted, otherwise an empty list
    """
    if delete_all:
        query = "DELETE FROM messages WHERE userId = ?"
        args = (user_id,)
        dbmanager.query(query=query, args=args)
        return []
    else:
        query = "DELETE FROM messages WHERE userId = ? AND msgId = ?"
        args = (user_id, msg_id)
        dbmanager.query(query=query, args=args)  
        messages = load_messages(user_id=user_id, dbmanager=dbmanager) 

        return messages 


def get_modified_files(start_timestamp: float, end_timestamp: float, source_dir: str ) -> List[str]:
    """
    Get a list of files that were modified within the specified timestamp range 

    :param start_timestamp: The start timestamp to filter modified files
    :param end_timestamp: The end timestamp to filter modified files
    :param source_dir: The directory to search for modified files
     
    :return: A list of file paths that were modified within the timestamp range
    """
    modified_files = []
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            file_path = os.path.join(root, file)
            file_mtime = os.path.getmtime(file_path)
            if start_timestamp < file_mtime < end_timestamp:
                uid = source_dir.split("/")[-1]
                modified_files.append(f"files/user/{uid}/{file}")  
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
                skills.append({"name": skill_name, "content": skill_content, "file_name":file})
    return skills

def get_all_skills(user_skills_path: str, global_skills_path: str, dest_dir:str =None) -> List[Dict[str, str]]:
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
        # check 
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