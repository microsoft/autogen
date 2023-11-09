import hashlib 
from .datamodel import Message 
from .db import DBManager 
import os
from shutil import copy2

def md5_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def save_message(message: Message, dbmanager: DBManager):
    query = "INSERT INTO messages (userId, rootMsgId, msgId, role, content, metadata, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)"
    args = (message.userId, message.rootMsgId, message.msgId, message.role, message.content, message.metadata, message.timestamp) 
    dbmanager.query(query=query, args=args)

def load_messages(user_id: str, dbmanager: DBManager):
    query = "SELECT * FROM messages WHERE userId = ?"
    args = (user_id,)
    result = dbmanager.query(query=query, args=args, json=True)
    # sort by timestamp desc 
    result = sorted(result, key=lambda k: k["timestamp"], reverse=False)
    return result

def delete_message(user_id: str, msg_id: str, dbmanager: DBManager, all=False,):
    if all:
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
    


def get_modified_files(start_timestamp, end_timestamp, source_dir, dest_dir):
    """
    Returns a list of files that have been changed or created in the source_dir between
    two timestamps and copies them to the dest_dir.

    :param start_timestamp: The start of the time interval as a timestamp
    :param end_timestamp: The end of the time interval as a timestamp
    :param source_dir: The directory to search for modified files
    :param dest_dir: The directory where modified files will be copied to
    :return: A list of paths to the modified files within the source_dir
    """
    modified_files = []
    for root, dirs, files in os.walk(source_dir):
        for file in files:
            file_path = os.path.join(root, file)
            file_mtime = os.path.getmtime(file_path)
            if start_timestamp < file_mtime < end_timestamp:
                uid = dest_dir.split("/")[-1]
                modified_files.append(f"files/user/{uid}/{file}")
                dest_file_path = os.path.join(dest_dir, os.path.relpath(file_path, start=source_dir))
                os.makedirs(os.path.dirname(dest_file_path), exist_ok=True)
                copy2(file_path, dest_file_path)
    return modified_files