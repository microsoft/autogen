# filename: server.py
import threading
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi import HTTPException

# pylint: disable=no-name-in-module
from pydantic import BaseModel
from typing import Optional
from rich import print as rprint

from datetime import datetime
from time import sleep, time

import sqlite3
import os
import json

import traceback
import message_handler
from message_handler import AgentWorkFlow

from utils.code_utils import utils_2_skills
from setup_db import create_db

from utils import create_llm_config

app = FastAPI()
lock = threading.Lock()

# allow cross origin requests for testing on localhost:800* ports only
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8001",
        "http://localhost:8081",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

root_file_path = os.path.dirname(os.path.abspath(__file__))
files_static_root = os.path.join(root_file_path, "files/")
static_folder_root = os.path.join(root_file_path, "ui")

os.makedirs(files_static_root, exist_ok=True)
os.makedirs(os.path.join(files_static_root, "user"), exist_ok=True)
os.makedirs(static_folder_root, exist_ok=True)


api = FastAPI(root_path="/api")
# mount an api route such that the main route serves the ui and the /api
# route serves the api operations.
app.mount("/api", api)

app.mount("/", StaticFiles(directory=static_folder_root, html=True), name="ui")
api.mount("/files", StaticFiles(directory=files_static_root, html=True), name="files")


class Message(BaseModel):
    userId: str
    rootMsgId: int
    msgId: int
    role: str
    content: str
    timestamp: datetime
    use_cache: Optional[bool] = False
    personalize: Optional[bool] = False
    ra: Optional[AgentWorkFlow] = AgentWorkFlow.CODER_ONLY


class Profile(BaseModel):
    userId: str
    profile: str


def create_message_table_if_not_exist():
    create_db()


def create_personalization_profile_table_if_not_exist():
    try:
        try:
            lock.acquire(True)
            conn = sqlite3.connect("database.sqlite")
            cursor = conn.cursor()
            cursor.execute(
                """
        CREATE TABLE IF NOT EXISTS personalization_profiles (
            userId INTEGER NOT NULL,
            profile TEXT,
            timestamp DATETIME NOT NULL,
            UNIQUE (userId)
        )
        """
            )
            conn.commit()
            cursor.close()
            conn.close()
        finally:
            lock.release()
    except Exception as e:
        print(f"Error creating table: {e}")


create_message_table_if_not_exist()
create_personalization_profile_table_if_not_exist()


def query_db(query, args=(), one=False):
    try:
        try:
            lock.acquire(True)
            conn = sqlite3.connect("database.sqlite")
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, args)
            result = cursor.fetchall()
            cursor.close()
            conn.close()
            # Convert rows to dictionaries
            json_result = [dict(row) for row in result]
            return (json_result[0] if json_result else None) if one else json_result
        finally:
            lock.release()
    except Exception as e:
        print(f"Error querying table: {e}")


def insert_db(query, args=()):
    try:
        try:
            lock.acquire(True)
            conn = sqlite3.connect("database.sqlite")
            cursor = conn.cursor()
            cursor.execute(query, args)
            conn.commit()
            cursor.close()
            conn.close()
        finally:
            lock.release()
    except Exception as e:
        print(f"Error inserting into db table: {e}")


def get_highest_msg_id_for_user_and_root(user_id, root_msg_id):
    try:
        try:
            lock.acquire(True)
            # Connect to the database (or create a new one if it doesn't exist)
            conn = sqlite3.connect("database.sqlite")

            # Create a cursor object to execute SQL commands
            cursor = conn.cursor()

            # Select the highest msgId from the messages table for the given userId and rootMsgId
            cursor.execute(
                "SELECT MAX(msgId) FROM messages WHERE userId = ? AND rootMsgId = ?",
                (user_id, root_msg_id),
            )

            # Fetch the result
            result = cursor.fetchone()

            cursor.close()
            # Close the connection
            conn.close()

            # Return the highest msgId if it exists, otherwise return -1
            if result[0] is not None:
                return result[0]
            else:
                return -1
        finally:
            lock.release()
    except Exception as e:
        print(f"Error getting highest msg_id from table table: {e}")


def get_md5_hash(string):
    import hashlib

    return hashlib.md5(string.encode()).hexdigest()


# Example usage:
path_to_config_list = "./OAI_CONFIG_LIST"
resulting_config = create_llm_config(path_to_config_list)


def handle_message(message: Message, ra_type=AgentWorkFlow.CODER_ONLY, enable_personalization=False):
    all_user_messages = get_messages(message.userId)["data"]
    messages = all_user_messages[:-1]
    # Inserting this assert because previous statement assumes that the last message
    # in the database is from the user.
    assert all_user_messages[-1]["role"] == "user"

    # Setup the work_dir and utils_dir
    usermd5 = get_md5_hash(message.userId)
    global_utils_dir = get_global_utils_dir()
    user_utils_dir = get_user_utils_dir(message.userId)
    if not os.path.exists(user_utils_dir):
        os.makedirs(user_utils_dir)
    utils_dir = [global_utils_dir, user_utils_dir]

    work_dir = os.path.join("files/user", usermd5, "work_dir")
    if not os.path.exists(work_dir):
        os.makedirs(work_dir)

    # Get the user's personalization profile
    personalization_profile = None
    if enable_personalization:
        personalization_profile = query_db(
            "SELECT profile FROM personalization_profiles WHERE userId = ?",
            (message.userId,),
        )
        if len(personalization_profile) > 0:
            personalization_profile = personalization_profile[0]["profile"]

    rprint(
        """\n\n\n\n
[italic red]--------------------------Handing new user message------------------------------[/italic red]
\n\n\n\n
"""
    )
    response = message_handler.process_user_message(
        message.content.strip(),
        history=messages,
        utils_dir=utils_dir,
        work_dir=work_dir,
        ra_type=ra_type,
        silent=False,
        # agent_on_receive=pretty_print_agent_message,
        path_to_config_list="./OAI_CONFIG_LIST",
        personalization_profile=personalization_profile,
    )

    # set the metadata
    metadata = {
        "user_hash": get_md5_hash(message.userId),
    }

    metadata["code"] = response["code"]
    message = response["content"]

    # remove the exitcode and code output from the message

    message = message.replace("exitcode: 0 (execution succeeded)\nCode output:", "")
    if message.strip() == "":
        message = "Task execution complete."
    for k in response["metadata"]:
        metadata[k] = response["metadata"][k]

    return {
        "status": True,
        "message": message,
        "metadata": metadata,
        "response_type": "text",
    }


@api.get("/messages")
def get_messages(user_id: str = None):
    if user_id is None:
        messages = []
    else:
        messages = query_db("SELECT * FROM messages WHERE userId = ?", (user_id,))
    return {
        "status": True,
        "data": messages,
        "message": "Messages retrieved successfully",
    }


class DeleteMessageModel(BaseModel):
    userId: str
    msgId: int


@api.post("/messages/delete")
async def delete_messages(req: DeleteMessageModel):
    userId = req.userId
    msgId = req.msgId

    try:
        insert_db(
            "DELETE FROM messages WHERE userId = ? AND msgId = ?",
            (
                userId,
                msgId,
            ),
        )
        print("*** Message deleted successfully")
        messages = query_db("SELECT * FROM messages WHERE userId = ?", (userId,))
        return {
            "status": True,
            "message": "Message deleted successfully",
            "data": messages,
        }
    except Exception as ex_error:
        print(ex_error)
        return {
            "status": False,
            "message": "Error occurred while deleting message: " + str(ex_error),
        }


@api.post("/messages")
async def add_message(message: Message):
    rootMsgId = 0
    userId = message.userId
    msgId = get_highest_msg_id_for_user_and_root(userId, rootMsgId) + 1
    personalize = message.personalize if message.personalize is not None else False
    ra_type = message.ra if message.ra is not None else AgentWorkFlow.CODER_ONLY

    message.rootMsgId = rootMsgId
    message.msgId = msgId

    print("Root Msg id and msg id", rootMsgId, msgId)

    try:
        insert_db(
            "INSERT INTO messages (userId, rootMsgId, msgId, role, content, metadata, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                message.userId,
                message.rootMsgId,
                message.msgId,
                message.role,
                message.content,
                # There is no metadata in user messages only in assistant messages
                None,
                message.timestamp,
            ),
        )

        # TODO: We will want a toggle or parameter for personalization

        start_time = time()
        response = handle_message(message, enable_personalization=personalize, ra_type=ra_type)

        current_timestamp = datetime.now()
        end_time = time()

        # Ensure all calls take at least 0.7s
        sleep_for = 0.7 - (end_time - start_time)
        if sleep_for > 0:
            sleep(sleep_for)

        responseMsgId = message.msgId + 1

        insert_db(
            "INSERT INTO messages (userId, rootMsgId, msgId, role, content, metadata, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                message.userId,
                message.rootMsgId,
                responseMsgId,
                "assistant",
                response["message"],
                json.dumps(response["metadata"]),
                current_timestamp,
            ),
        )

        response["msgId"] = responseMsgId

        return response
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=400,
            detail="Message with the same rootMsgId and msgId already exists.",
        )
    except Exception as ex_error:
        print("Error processing message", str(ex_error))
        traceback.print_exc()
        return {
            "status": False,
            "message": "Error occurred while processing message: " + str(ex_error),
        }


@api.get("/profile")
def get_profile(user_id: str = None):
    if user_id is None:
        profile = ""
    else:
        profile = query_db("SELECT profile FROM personalization_profiles WHERE userId = ?", (user_id,))
        if len(profile) == 0:
            profile = ""
        else:
            profile = profile[0]

    return {
        "status": True,
        "data": profile,
        "message": "Profile data retrieved successfully",
    }


@api.post("/profile")
async def set_profile(req: Profile):
    current_timestamp = datetime.now()
    try:
        insert_db(
            """
INSERT INTO personalization_profiles (userId, profile, timestamp)
  VALUES(?, ?, ?)
  ON CONFLICT(userId)
  DO UPDATE SET profile=?, timestamp=?
  """,
            (
                req.userId,
                req.profile,
                current_timestamp,
                req.profile,
                current_timestamp,
            ),
        )
        return {
            "status": True,
            "data": {"profile": req.profile},
            "message": "Profile updated successfully",
        }
    except Exception as ex_error:
        print(ex_error)
        return {
            "status": False,
            "message": "Error occurred while processing message: " + str(ex_error),
        }


@api.get("/profile/refresh")
def refresh_profile(user_id: str = None):
    from message_handler import generate_oai_reply
    import autogen

    window_size = 15
    path_to_config_list = "./OAI_CONFIG_LIST"
    llm_config = create_llm_config(path_to_config_list)

    # Get the user messages
    # TODO: This should later be refactored, as it is redundant and was
    # verbatim copied from the api get messages route
    if user_id is None:
        return {
            "status": False,
            "message": "No user_id specified.",
        }
    else:
        conversation_history = query_db("SELECT * FROM messages WHERE userId = ?", (user_id,))

    # Get the user profile
    # TODO: This should later be refactored, as it is redundant and was
    # verbatim copied from the api get profile route
    old_profile = query_db("SELECT profile FROM personalization_profiles WHERE userId = ?", (user_id,))
    if len(old_profile) == 0:
        old_profile = ""
    else:
        old_profile = old_profile[0]["profile"]

    # Create a truncated and abridged transcript from which to infer user preferences
    transcript = ""
    n_user_messages = 0

    # How do we abridge assitant messages
    ASSISTANT_MESSAGE_START_LEN = 100
    ASSISTANT_MESSAGE_END_LEN = 100

    for i in range(0, window_size):
        # Run backward over the last few messages
        idx = len(conversation_history) - (i + 1)
        if idx < 0:
            break

        message = conversation_history[idx]

        if message["role"] == "user":
            n_user_messages += 1
            transcript = "USER: " + message["content"].strip() + "\n\n" + transcript
        elif message["role"] == "assistant":
            abridged_message = message["content"].strip()

            # Abridge the message
            if len(abridged_message) > ASSISTANT_MESSAGE_START_LEN + ASSISTANT_MESSAGE_END_LEN:
                abridged_message = (
                    abridged_message[0:ASSISTANT_MESSAGE_START_LEN]
                    + " (...) "
                    + abridged_message[len(abridged_message) - (ASSISTANT_MESSAGE_END_LEN) :]
                )

            transcript = "ASSISTANT: " + abridged_message + "\n\n" + transcript

    # Nothing to do
    if len(transcript) == 0 or n_user_messages == 0:
        return {
            "status": True,
            "data": {"profile": old_profile},
            "message": "Profile refreshed successfully",
        }

    # Create the prompt detailing what we already know about the user
    known_info = ""
    prompt_suffix = ""
    if old_profile is None or len(old_profile) == 0:
        known_info = "Not much is currently known about USER. They have no BIOGRAPHY on file."
        prompt_suffix = "."
    else:
        known_info = (
            "From prior conversation with USER, we have the following BIOGRAPHY about them on file:\n" + old_profile
        )
        prompt_suffix = ", as well as any prior assumptions about the user that need to be revised."

    # Ok, now for the main prompt
    prompt = (
        """
An AI ASSISTANT like yourself can learn a lot about a USER by engaging them in conversation. For example, if a USER asks an ASSISTANT to reformat a previous answer in bullet points, then we may infer that the USER prefers concise communication. Likewise if they ask to see programming code, we may infer that the USER is comfortable with that programming language. Finally, if they repeatedly ask an ASSISTANT about information about a particular research topic, we may infer they are interested in that topic. These are only a few examples.

%s

Consider the following transcript of the most recent conversation between an ASSISTANT and USER. Please summarize what new information this transcript reveals about the USER%s

Here is the transcript:
%s
"""
        % (known_info, prompt_suffix, transcript)
    ).strip()

    # Call OpenAI to generate the completion
    messages = [{"role": "user", "content": prompt}]
    new_info = generate_oai_reply(messages, llm_config)
    messages.append({"role": "assistant", "content": new_info})
    messages.append(
        {
            "role": "user",
            "content": "Based in this information, write a new BIOGRAPHY about the USER. The biography should be at most 2 paragraphs.",
        }
    )

    revised_bio = generate_oai_reply(messages, llm_config)

    # Update the database
    # TODO: This should later be refactored, as it is redundant and was
    # verbatim copied from the api post profile route
    current_timestamp = datetime.now()
    try:
        insert_db(
            """
INSERT INTO personalization_profiles (userId, profile, timestamp)
  VALUES(?, ?, ?)
  ON CONFLICT(userId)
  DO UPDATE SET profile=?, timestamp=?
  """,
            (
                user_id,
                revised_bio,
                current_timestamp,
                revised_bio,
                current_timestamp,
            ),
        )
        return {
            "status": True,
            "data": {"profile": revised_bio},
            "message": "Profile refreshed successfully",
        }
    except Exception as ex_error:
        print(ex_error)
        return {
            "status": False,
            "message": "Error occurred while processing message: " + str(ex_error),
        }


def get_user_utils_dir(user_id) -> str:
    user_utils_dir = os.path.join("files/user", get_md5_hash(user_id), "utils_dir")
    if not os.path.exists(user_utils_dir):
        os.makedirs(user_utils_dir, exist_ok=True)
    return user_utils_dir


def get_global_utils_dir() -> str:
    return os.path.join("files/", "global_utils_dir")


@api.get("/skills")
def get_skills(user_id: str):
    user_utils_dir = get_user_utils_dir(user_id)
    global_utils_dir = get_global_utils_dir()
    utils_dir = [global_utils_dir, user_utils_dir]

    skills = utils_2_skills(utils_dir)

    return {
        "status": True,
        "message": "Skills retrieved successfully",
        "skills": skills,
    }


@api.get("/skills/clear")
def clear_skills(user_id: str):
    # empty the content of files in the user utils dir
    user_utils_dir = get_user_utils_dir(user_id)

    user_files = os.listdir(user_utils_dir)
    for f in user_files:
        with open(os.path.join(user_utils_dir, f), "w") as fp:
            fp.write("")
    global_utils_dir = get_global_utils_dir()
    utils_dir = [global_utils_dir, user_utils_dir]
    skills = utils_2_skills(utils_dir)

    return {
        "status": True,
        "message": "User Skills cleared successfully",
        "skills": skills,
    }


class ClearDBModel(BaseModel):
    userId: str


@api.post("/cleardb")
async def clear_db(req: ClearDBModel):
    """Clear user conversation history database"""
    userId = req.userId

    # also delete all files in the users work_dir
    user_dir = os.path.join("files/user", get_md5_hash(userId), "work_dir")
    # check if the user_dir exists else create if
    if not os.path.exists(user_dir):
        os.makedirs(user_dir, exist_ok=True)
    content = os.listdir(user_dir)
    files = [f for f in content if os.path.isfile(os.path.join(user_dir, f))]
    rprint(f"[italic yellow]INFO: /cleardb Deleting files from work_dir:[/italic yellow] {files}")
    for f in files:
        os.remove(os.path.join(user_dir, f))

    try:
        insert_db(
            "DELETE FROM messages WHERE userId = ?",
            (userId,),
        )
        return {
            "status": "success",
            "message": "Messages and files cleared successfully",
        }

    except sqlite3.Error as e:
        raise HTTPException(
            status_code=400,
            detail="Error occurred while clearing messages: " + str(e),
        )


def get_all_filepaths_in_directory(directory):
    filepaths = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in (".cache", "__pycache__")]
        for file in files:
            filepaths.append(os.path.join(root, file))
    return filepaths


@api.get("/userfiles")
def get_user_files(user_id: str):
    user_dir = os.path.join("files/user", get_md5_hash(user_id))
    if not os.path.exists(user_dir):
        os.makedirs(user_dir, exist_ok=True)
    all_filepaths = get_all_filepaths_in_directory(user_dir)
    print(all_filepaths)

    return {
        "status": True,
        "message": "User files retrieved successfully",
        "files": all_filepaths,
    }


@api.get("/ras")
def get_available_ras():
    return {
        "status": True,
        "message": "Available RAs retrieved successfully",
        "data": message_handler.AVAILABLE_RAS,
    }
