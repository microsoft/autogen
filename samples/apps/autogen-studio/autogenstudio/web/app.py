import asyncio
from contextlib import asynccontextmanager
import json
import os
import queue
import threading
import traceback
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi import HTTPException
from openai import OpenAIError
from ..version import VERSION

from ..datamodel import (
    DBWebRequestModel,
    DeleteMessageWebRequestModel,
    Message,
    Session,
)
from ..utils import md5_hash, init_webserver_folders, DBManager, dbutils, test_model
from ..chatmanager import AutoGenChatManager, WebSocketConnectionManager


managers = {"chat": None}  # manage calls to autogen
# Create thread-safe queue for messages between api thread and autogen threads
message_queue = queue.Queue()
active_connections = []
active_connections_lock = asyncio.Lock()
websocket_manager = WebSocketConnectionManager(
    active_connections=active_connections, active_connections_lock=active_connections_lock
)


def message_handler():
    while True:
        message = message_queue.get()
        print("Active Connections: ", [client_id for _, client_id in websocket_manager.active_connections])
        print("Current message connection id: ", message["connection_id"])
        for connection, socket_client_id in websocket_manager.active_connections:
            if message["connection_id"] == socket_client_id:
                asyncio.run(websocket_manager.send_message(message, connection))
        message_queue.task_done()


message_handler_thread = threading.Thread(target=message_handler, daemon=True)
message_handler_thread.start()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("***** App started *****")
    managers["chat"] = AutoGenChatManager(message_queue=message_queue)

    yield
    # Close all active connections
    await websocket_manager.disconnect_all()
    print("***** App stopped *****")


app = FastAPI(lifespan=lifespan)


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


root_file_path = os.environ.get("AUTOGENSTUDIO_APPDIR") or os.path.dirname(os.path.abspath(__file__))
# init folders skills, workdir, static, files etc
folders = init_webserver_folders(root_file_path)
ui_folder_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")

api = FastAPI(root_path="/api")
# mount an api route such that the main route serves the ui and the /api
app.mount("/api", api)

app.mount("/", StaticFiles(directory=ui_folder_path, html=True), name="ui")
api.mount("/files", StaticFiles(directory=folders["files_static_root"], html=True), name="files")


db_path = os.path.join(root_file_path, "database.sqlite")
dbmanager = DBManager(path=db_path)  # manage database operations
# manage websocket connections


@api.post("/messages")
async def add_message(req: DBWebRequestModel):
    message = Message(**req.message.dict())
    user_history = dbutils.get_messages(user_id=message.user_id, session_id=req.message.session_id, dbmanager=dbmanager)

    # save incoming message to db
    dbutils.create_message(message=message, dbmanager=dbmanager)
    user_dir = os.path.join(folders["files_static_root"], "user", md5_hash(message.user_id))
    os.makedirs(user_dir, exist_ok=True)

    try:
        response_message: Message = managers["chat"].chat(
            message=message,
            history=user_history,
            user_dir=user_dir,
            flow_config=req.workflow,
            connection_id=req.connection_id,
        )

        # save agent's response to db
        messages = dbutils.create_message(message=response_message, dbmanager=dbmanager)
        response = {
            "status": True,
            "message": "Message processed successfully",
            "data": messages,
            # "metadata": json.loads(response_message.metadata),
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


@api.post("/sessions/rename")
async def rename_user_session(name: str, req: DBWebRequestModel):
    """Rename a session for a user"""
    print("Rename: " + name)
    print("renaming session for user: " + req.user_id + " to: " + name)
    try:
        session = dbutils.rename_session(name=name, session=req.session, dbmanager=dbmanager)
        return {
            "status": True,
            "message": "Session renamed successfully",
            "data": session,
        }
    except Exception as ex_error:
        print(traceback.format_exc())
        return {
            "status": False,
            "message": "Error occurred while renaming session: " + str(ex_error),
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


@api.get("/models")
async def get_user_models(user_id: str):
    try:
        models = dbutils.get_models(user_id, dbmanager=dbmanager)

        return {
            "status": True,
            "message": "Models retrieved successfully",
            "data": models,
        }
    except Exception as ex_error:
        print(ex_error)
        return {
            "status": False,
            "message": "Error occurred while retrieving models: " + str(ex_error),
        }


@api.post("/models")
async def create_user_models(req: DBWebRequestModel):
    """Create a new model for a user"""

    try:
        models = dbutils.upsert_model(model=req.model, dbmanager=dbmanager)

        return {
            "status": True,
            "message": "Model created successfully",
            "data": models,
        }

    except Exception as ex_error:
        print(traceback.format_exc())
        return {
            "status": False,
            "message": "Error occurred while creating model: " + str(ex_error),
        }


@api.post("/models/test")
async def test_user_models(req: DBWebRequestModel):
    """Test a model to verify it works"""

    try:
        response = test_model(model=req.model)
        return {
            "status": True,
            "message": "Model tested successfully",
            "data": response,
        }

    except OpenAIError as oai_error:
        print(traceback.format_exc())
        return {
            "status": False,
            "message": "Error occurred while testing model: " + str(oai_error),
        }
    except Exception as ex_error:
        print(traceback.format_exc())
        return {
            "status": False,
            "message": "Error occurred while testing model: " + str(ex_error),
        }


@api.delete("/models/delete")
async def delete_user_model(req: DBWebRequestModel):
    """Delete a model for a user"""

    try:
        models = dbutils.delete_model(model=req.model, dbmanager=dbmanager)

        return {
            "status": True,
            "message": "Model deleted successfully",
            "data": models,
        }

    except Exception as ex_error:
        print(traceback.format_exc())
        return {
            "status": False,
            "message": "Error occurred while deleting model: " + str(ex_error),
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


@api.get("/version")
async def get_version():
    return {
        "status": True,
        "message": "Version retrieved successfully",
        "data": {"version": VERSION},
    }


async def process_socket_message(data: dict, websocket: WebSocket, client_id: str):
    print(f"Client says: {data['type']}")
    if data["type"] == "user_message":
        user_request_body = DBWebRequestModel(**data["data"])
        response = await add_message(user_request_body)
        response_socket_message = {
            "type": "agent_response",
            "data": response,
            "connection_id": client_id,
        }
        await websocket_manager.send_message(response_socket_message, websocket)


@api.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket_manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_json()
            await process_socket_message(data, websocket, client_id)
    except WebSocketDisconnect:
        print(f"Client #{client_id} is disconnected")
        await websocket_manager.disconnect(websocket)
