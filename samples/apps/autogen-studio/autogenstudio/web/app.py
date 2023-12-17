import json
import os
import traceback
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi import HTTPException


from ..datamodel import (
    ChatWebRequestModel,
    DBWebRequestModel,
    DeleteMessageWebRequestModel,
    Message,
    Session,
)
from ..utils import md5_hash, init_webserver_folders, DBManager, dbutils

from ..chatmanager import AutoGenChatManager


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
# init folders skills, workdir, static, files etc
folders = init_webserver_folders(root_file_path)

api = FastAPI(root_path="/api")
# mount an api route such that the main route serves the ui and the /api
app.mount("/api", api)

app.mount("/", StaticFiles(directory=folders["static_folder_root"], html=True), name="ui")
api.mount("/files", StaticFiles(directory=folders["files_static_root"], html=True), name="files")


db_path = os.path.join(root_file_path, "database.sqlite")
dbmanager = DBManager(path=db_path)  # manage database operations
chatmanager = AutoGenChatManager()  # manage calls to autogen


@api.post("/messages")
async def add_message(req: ChatWebRequestModel):
    message = Message(**req.message.dict())
    user_history = dbutils.get_messages(user_id=message.user_id, session_id=req.message.session_id, dbmanager=dbmanager)

    # save incoming message to db
    dbutils.create_message(message=message, dbmanager=dbmanager)
    user_dir = os.path.join(folders["files_static_root"], "user", md5_hash(message.user_id))
    os.makedirs(user_dir, exist_ok=True)

    try:
        response_message: Message = chatmanager.chat(
            message=message,
            history=user_history,
            work_dir=user_dir,
            flow_config=req.flow_config,
        )

        # save assistant response to db
        dbutils.create_message(message=response_message, dbmanager=dbmanager)
        response = {
            "status": True,
            "message": response_message.content,
            "metadata": json.loads(response_message.metadata),
        }
        return response
    except Exception as ex_error:
        print(traceback.format_exc())
        return {
            "status": False,
            "message": "Error occurred while processing message: " + str(ex_error),
        }


@api.get("/messages")
async def get_messages(user_id: str = None, session_id: str = None):
    if user_id is None:
        raise HTTPException(status_code=400, detail="user_id is required")
    try:
        user_history = dbutils.get_messages(user_id=user_id, session_id=session_id, dbmanager=dbmanager)

        return {
            "status": True,
            "data": user_history,
            "message": "Messages retrieved successfully",
        }
    except Exception as ex_error:
        print(ex_error)
        return {
            "status": False,
            "message": "Error occurred while retrieving messages: " + str(ex_error),
        }


@api.get("/gallery")
async def get_gallery_items(gallery_id: str = None):
    try:
        gallery = dbutils.get_gallery(gallery_id=gallery_id, dbmanager=dbmanager)
        return {
            "status": True,
            "data": gallery,
            "message": "Gallery items retrieved successfully",
        }
    except Exception as ex_error:
        print(ex_error)
        return {
            "status": False,
            "message": "Error occurred while retrieving messages: " + str(ex_error),
        }


@api.get("/sessions")
async def get_user_sessions(user_id: str = None):
    """Return a list of all sessions for a user"""
    if user_id is None:
        raise HTTPException(status_code=400, detail="user_id is required")

    try:
        user_sessions = dbutils.get_sessions(user_id=user_id, dbmanager=dbmanager)

        return {
            "status": True,
            "data": user_sessions,
            "message": "Sessions retrieved successfully",
        }
    except Exception as ex_error:
        print(ex_error)
        return {
            "status": False,
            "message": "Error occurred while retrieving sessions: " + str(ex_error),
        }


@api.post("/sessions")
async def create_user_session(req: DBWebRequestModel):
    """Create a new session for a user"""
    # print(req.session, "**********" )

    try:
        session = Session(user_id=req.session.user_id, flow_config=req.session.flow_config)
        user_sessions = dbutils.create_session(user_id=req.user_id, session=session, dbmanager=dbmanager)
        return {
            "status": True,
            "message": "Session created successfully",
            "data": user_sessions,
        }
    except Exception as ex_error:
        print(traceback.format_exc())
        return {
            "status": False,
            "message": "Error occurred while creating session: " + str(ex_error),
        }


@api.post("/sessions/publish")
async def publish_user_session_to_gallery(req: DBWebRequestModel):
    """Create a new session for a user"""

    try:
        gallery_item = dbutils.create_gallery(req.session, tags=req.tags, dbmanager=dbmanager)
        return {
            "status": True,
            "message": "Session successfully published",
            "data": gallery_item,
        }
    except Exception as ex_error:
        print(traceback.format_exc())
        return {
            "status": False,
            "message": "Error occurred  while publishing session: " + str(ex_error),
        }


@api.delete("/sessions/delete")
async def delete_user_session(req: DBWebRequestModel):
    """Delete a session for a user"""

    try:
        sessions = dbutils.delete_session(session=req.session, dbmanager=dbmanager)
        return {
            "status": True,
            "message": "Session deleted successfully",
            "data": sessions,
        }
    except Exception as ex_error:
        print(traceback.format_exc())
        return {
            "status": False,
            "message": "Error occurred while deleting session: " + str(ex_error),
        }


@api.post("/messages/delete")
async def remove_message(req: DeleteMessageWebRequestModel):
    """Delete a message from the database"""

    try:
        messages = dbutils.delete_message(
            user_id=req.user_id, msg_id=req.msg_id, session_id=req.session_id, dbmanager=dbmanager
        )
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


@api.get("/skills")
async def get_user_skills(user_id: str):
    try:
        skills = dbutils.get_skills(user_id, dbmanager=dbmanager)

        return {
            "status": True,
            "message": "Skills retrieved successfully",
            "data": skills,
        }
    except Exception as ex_error:
        print(ex_error)
        return {
            "status": False,
            "message": "Error occurred while retrieving skills: " + str(ex_error),
        }


@api.post("/skills")
async def create_user_skills(req: DBWebRequestModel):
    try:
        skills = dbutils.upsert_skill(skill=req.skill, dbmanager=dbmanager)

        return {
            "status": True,
            "message": "Skills retrieved successfully",
            "data": skills,
        }

    except Exception as ex_error:
        print(ex_error)
        return {
            "status": False,
            "message": "Error occurred while creating skills: " + str(ex_error),
        }


@api.delete("/skills/delete")
async def delete_user_skills(req: DBWebRequestModel):
    """Delete a skill for a user"""

    try:
        skills = dbutils.delete_skill(req.skill, dbmanager=dbmanager)

        return {
            "status": True,
            "message": "Skill deleted successfully",
            "data": skills,
        }

    except Exception as ex_error:
        print(ex_error)
        return {
            "status": False,
            "message": "Error occurred while deleting skill: " + str(ex_error),
        }


@api.get("/agents")
async def get_user_agents(user_id: str):
    try:
        agents = dbutils.get_agents(user_id, dbmanager=dbmanager)

        return {
            "status": True,
            "message": "Agents retrieved successfully",
            "data": agents,
        }
    except Exception as ex_error:
        print(ex_error)
        return {
            "status": False,
            "message": "Error occurred while retrieving agents: " + str(ex_error),
        }


@api.post("/agents")
async def create_user_agents(req: DBWebRequestModel):
    """Create a new agent for a user"""

    try:
        agents = dbutils.upsert_agent(agent_flow_spec=req.agent, dbmanager=dbmanager)

        return {
            "status": True,
            "message": "Agent created successfully",
            "data": agents,
        }

    except Exception as ex_error:
        print(traceback.format_exc())
        return {
            "status": False,
            "message": "Error occurred while creating agent: " + str(ex_error),
        }


@api.delete("/agents/delete")
async def delete_user_agent(req: DBWebRequestModel):
    """Delete an agent for a user"""

    try:
        agents = dbutils.delete_agent(agent=req.agent, dbmanager=dbmanager)

        return {
            "status": True,
            "message": "Agent deleted successfully",
            "data": agents,
        }

    except Exception as ex_error:
        print(traceback.format_exc())
        return {
            "status": False,
            "message": "Error occurred while deleting agent: " + str(ex_error),
        }


@api.get("/workflows")
async def get_user_workflows(user_id: str):
    try:
        workflows = dbutils.get_workflows(user_id, dbmanager=dbmanager)

        return {
            "status": True,
            "message": "Workflows retrieved successfully",
            "data": workflows,
        }
    except Exception as ex_error:
        print(ex_error)
        return {
            "status": False,
            "message": "Error occurred while retrieving workflows: " + str(ex_error),
        }


@api.post("/workflows")
async def create_user_workflow(req: DBWebRequestModel):
    """Create a new workflow for a user"""

    try:
        workflow = dbutils.upsert_workflow(workflow=req.workflow, dbmanager=dbmanager)
        return {
            "status": True,
            "message": "Workflow created successfully",
            "data": workflow,
        }

    except Exception as ex_error:
        print(ex_error)
        return {
            "status": False,
            "message": "Error occurred while creating workflow: " + str(ex_error),
        }


@api.delete("/workflows/delete")
async def delete_user_workflow(req: DBWebRequestModel):
    """Delete a workflow for a user"""

    try:
        workflow = dbutils.delete_workflow(workflow=req.workflow, dbmanager=dbmanager)
        return {
            "status": True,
            "message": "Workflow deleted successfully",
            "data": workflow,
        }

    except Exception as ex_error:
        print(ex_error)
        return {
            "status": False,
            "message": "Error occurred while deleting workflow: " + str(ex_error),
        }
