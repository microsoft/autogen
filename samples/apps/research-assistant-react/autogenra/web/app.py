import json
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi import HTTPException
from ..db import DBManager
from ..datamodel import Message, DeleteMessageModel,ClearDBModel
from ..chat import ChatManager
from ..utils import load_messages, md5_hash, save_message, delete_message, init_webserver_folders, skill_from_folder

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
folders = init_webserver_folders(root_file_path) # init folders skills, workdir, static, files etc

api = FastAPI(root_path="/api")
# mount an api route such that the main route serves the ui and the /api 
app.mount("/api", api)

app.mount("/", StaticFiles(directory=folders["static_folder_root"], html=True), name="ui")
api.mount("/files", StaticFiles(directory=folders["files_static_root"], html=True), name="files")


db_path = os.path.join(root_file_path, "database.sqlite")
dbmanager = DBManager(path=db_path) # manage database operations
chatmanager = ChatManager() # manage calls to autogen




@api.post("/messages")
async def add_message(message: Message):
    message  = Message(**message.dict()) 
    user_history = load_messages(user_id=message.userId, dbmanager=dbmanager)  

    # save incoming message to db
    save_message(message=message, dbmanager=dbmanager)
    user_dir = os.path.join(folders["files_static_root"], "user", md5_hash(message.userId))
    os.makedirs(user_dir, exist_ok=True)

    try: 
        response_message:Message = chatmanager.chat(message=message, history=user_history, work_dir=folders["workdir_root"], user_dir=user_dir)  
 
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
    

@api.get("/skills")
def get_skills(user_id: str): 
    user_skills_path = os.path.join(folders["user_skills_dir"], md5_hash(user_id))
    os.makedirs(user_skills_path, exist_ok=True)
    user_skills = skill_from_folder(user_skills_path)

    global_skils_path = folders["global_skills_dir"]
    global_skills = skill_from_folder(global_skils_path)

    skills = {
        "user": user_skills,
        "global": global_skills,
    }

    return {
        "status": True,
        "message": "Skills retrieved successfully",
        "skills": skills,
    }