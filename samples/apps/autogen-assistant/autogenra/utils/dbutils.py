
import json
import sqlite3
from typing import List
from ..datamodel import Message, Session
from ..db import DBManager




def save_message(message: Message, dbmanager: DBManager) -> None:
    """
    Save a message in the database using the provided database manager.

    :param message: The Message object containing message data
    :param dbmanager: The DBManager instance used to interact with the database
    """
    query = "INSERT INTO messages (user_id, root_msg_id, msg_id, role, content, metadata, timestamp, session_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
    args = (
        message.user_id,
        message.root_msg_id,
        message.msg_id,
        message.role,
        message.content,
        message.metadata,
        message.timestamp,
        message.session_id
    )
    dbmanager.query(query=query, args=args)


def load_messages(user_id: str,session_id: str, dbmanager: DBManager) -> List[dict]:
    """
    Load messages for a specific user and session from the database, sorted by timestamp.

    :param user_id: The ID of the user whose messages are to be loaded
    :param session_id: The ID of the session whose messages are to be loaded
    :param dbmanager: The DBManager instance to interact with the database

    :return: A list of dictionaries, each representing a message
    """
    query = "SELECT * FROM messages WHERE user_id = ? AND session_id = ?"
    args = (user_id, session_id)
    result = dbmanager.query(query=query, args=args, json=True)
    # Sort by timestamp ascending
    result = sorted(result, key=lambda k: k["timestamp"], reverse=False)
    return result




   


def get_sessions(user_id: str, dbmanager: DBManager) -> List[dict]:
    """
    Load sessions for a specific user from the database, sorted by timestamp.

    :param user_id: The ID of the user whose sessions are to be loaded
    :param dbmanager: The DBManager instance to interact with the database
    :return: A list of dictionaries, each representing a session
    """
    query = "SELECT * FROM sessions WHERE user_id = ?"
    args = (user_id,)
    result = dbmanager.query(query=query, args=args, json=True)
    # Sort by timestamp ascending
    result = sorted(result, key=lambda k: k["timestamp"], reverse=False)
    for row in result:
        row["flow_config"] = json.loads(row["flow_config"])
    return result

def create_session(user_id: str, session: Session, dbmanager: DBManager) -> List[dict]:
    """
    Create a new session for a specific user in the database.

    :param user_id: The ID of the user whose session is to be created
    :param dbmanager: The DBManager instance to interact with the database
    :return: A list of dictionaries, each representing a session
    """
  
    query = "INSERT INTO sessions (user_id, session_id, timestamp, flow_config) VALUES (?, ?, ?,?)" 
    args = (session.user_id, session.session_id, session.timestamp,  json.dumps(session.flow_config.dict()))
    dbmanager.query(query=query, args=args)
    sessions = get_sessions(user_id=user_id, dbmanager=dbmanager)

    return sessions

def delete_user_sessions(user_id: str,session_id: str, dbmanager: DBManager, delete_all: bool = False) -> List[dict]: 
    """
    Delete a specific session or all sessions for a user from the database.

    :param user_id: The ID of the user whose session is to be deleted
    :param session_id: The ID of the specific session to be deleted (ignored if delete_all is True)
    :param dbmanager: The DBManager instance to interact with the database
    :param delete_all: If True, all sessions for the user will be deleted
    :return: A list of the remaining sessions if not all were deleted, otherwise an empty list
    """
    if delete_all:
        query = "DELETE FROM sessions WHERE user_id = ?"
        args = (user_id,)
        dbmanager.query(query=query, args=args)
        return []
    else:
        query = "DELETE FROM sessions WHERE user_id = ? AND session_id = ?"
        args = (user_id, session_id)
        dbmanager.query(query=query, args=args)
        sessions = get_sessions(user_id=user_id, dbmanager=dbmanager)

        return sessions



def delete_message(user_id: str, msg_id: str, session_id:str, dbmanager: DBManager, delete_all: bool = False) -> List[dict]:
    """
    Delete a specific message or all messages for a user and session from the database.

    :param user_id: The ID of the user whose messages are to be deleted
    :param msg_id: The ID of the specific message to be deleted (ignored if delete_all is True)
    :param session_id: The ID of the session whose messages are to be deleted
    :param dbmanager: The DBManager instance to interact with the database
    :param delete_all: If True, all messages for the user will be deleted
    :return: A list of the remaining messages if not all were deleted, otherwise an empty list
    """
    
    if delete_all:
        query = "DELETE FROM messages WHERE user_id = ? AND session_id = ?"
        args = (user_id, session_id)
        dbmanager.query(query=query, args=args)
        return []
    else:
        query = "DELETE FROM messages WHERE user_id = ? AND msg_id = ? AND session_id = ?"
        args = (user_id, msg_id, session_id)
        dbmanager.query(query=query, args=args)
        messages = load_messages(user_id=user_id, session_id=session_id, dbmanager=dbmanager)
        return messages
    

