import json
import os
from typing import List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi import HTTPException
from ..db import DBManager
from ..datamodel import Message, DeleteMessageModel,ClearDBModel
from ..chat import ChatManager
from ..utils import load_messages, md5_hash, save_message, delete_message
import uuid
import time

app = FastAPI()


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
workdir_root = os.path.join(root_file_path, "workdir")

os.makedirs(files_static_root, exist_ok=True)
os.makedirs(os.path.join(files_static_root, "user"), exist_ok=True)
os.makedirs(static_folder_root, exist_ok=True)
os.makedirs(workdir_root, exist_ok=True)


api = FastAPI(root_path="/api")
# mount an api route such that the main route serves the ui and the /api
# route serves the api operations.
app.mount("/api", api)

app.mount("/", StaticFiles(directory=static_folder_root, html=True), name="ui")
api.mount("/files", StaticFiles(directory=files_static_root, html=True), name="files")


db_path = os.path.join(root_file_path, "database.sqlite")
dbmanager = DBManager(path=db_path) 
chatmanager = ChatManager()




@api.post("/messages")
async def add_message(message: Message):
    message  = Message(**message.dict()) 
    user_history = load_messages(user_id=message.userId, dbmanager=dbmanager)  

    # save incoming message to db
    save_message(message=message, dbmanager=dbmanager)
    user_dir = os.path.join(files_static_root, "user", md5_hash(message.userId))
    os.makedirs(user_dir, exist_ok=True)

    try: 
        response_message:Message = chatmanager.chat(message=message, history=user_history, work_dir=workdir_root, user_dir=user_dir)  
 
        # save assistant response to db
        save_message(message=response_message, dbmanager=dbmanager) 
        response = {
            "status": True,
            "message": response_message.content,
            "metadata": json.loads(response_message.metadata),
            }
        return response
    except Exception as ex_error:
        print(ex_error)
        return {
            "status": False,
            "message": "Error occurred while processing message: " + str(ex_error),
        }

@api.get("/messages")
def get_messages(user_id: str = None):
    if user_id is None:
        raise HTTPException(status_code=400, detail="user_id is required")
    user_history = load_messages(user_id=user_id, dbmanager=dbmanager)

    return {
        "status": True,
        "data": user_history,
        "message": "Messages retrieved successfully",
    }

@api.post("/messages/delete")
async def remove_message(req: DeleteMessageModel): 
    """Delete a message from the database"""
    print(req)
    try:
        messages = delete_message(user_id=req.userId, msg_id=req.msgId, dbmanager=dbmanager)
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


 


@api.post("/cleardb")
async def clear_db(req: ClearDBModel):
    """Clear user conversation history database"""

    try:

        delete_message(user_id=req.userId, msg_id=None, dbmanager=dbmanager, all=True) 
        return {
            "status": True,
            "message": "Messages and files cleared successfully",
        }
    except Exception as ex_error:
        print(ex_error)
        return {
            "status": False,
            "message": "Error occurred while deleting message: " + str(ex_error),
        }