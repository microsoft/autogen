# /api/workflows routes
import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from loguru import logger
from pydantic import BaseModel

from ...datamodel import WorkflowDB
from ...workflow.core import Workflow, WorkflowRunner, WorkflowExecution, WorkflowStatus
from ..auth.dependencies import get_ws_auth_manager, get_current_user
from ..auth.models import User
from ..auth.wsauth import WebSocketAuthHandler
from ..deps import get_db

router = APIRouter()


class CreateWorkflowRequest(BaseModel):
    name: str
    description: str = ""
    config: Dict[str, Any]
    tags: list[str] = []
    user_id: str


class UpdateWorkflowRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    config: Dict[str, Any] | None = None
    tags: list[str] | None = None
    is_active: bool | None = None


class CreateWorkflowRunRequest(BaseModel):
    workflow_id: int | None = None
    workflow_config: Dict[str, Any] | None = None


# ==================== REST API Routes ====================

@router.get("/api/workflows")
async def list_workflows(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db=Depends(get_db)
) -> Dict[str, Any]:
    """List all workflows with optional filters"""
    try:
        workflows = db.get(WorkflowDB, filters={"user_id": user_id, "is_active": True})
        return {"status": True, "data": workflows.data or []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/workflows")
async def create_workflow(request: CreateWorkflowRequest, db=Depends(get_db)) -> Dict:
    """Create a new workflow"""
    try:
        workflow = db.upsert(
            WorkflowDB(
                name=request.name,
                description=request.description,
                config=request.config,
                tags=request.tags,
                user_id=request.user_id,
                is_active=True,
            ),
            return_json=False,
        )
        return {"status": workflow.status, "data": {"workflow_id": workflow.data.id}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/api/workflows/{workflow_id}")
async def get_workflow(workflow_id: int, user_id: str, db=Depends(get_db)) -> Dict:
    """Get workflow details"""
    try:
        workflow = db.get(WorkflowDB, filters={"id": workflow_id, "user_id": user_id}, return_json=False)
        if not workflow.status or not workflow.data:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return {"status": True, "data": workflow.data[0]}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/api/workflows/{workflow_id}")
async def update_workflow(
    workflow_id: int, request: UpdateWorkflowRequest, user_id: str, db=Depends(get_db)
) -> Dict:
    """Update workflow"""
    try:
        # First check if workflow exists and belongs to user
        existing = db.get(WorkflowDB, filters={"id": workflow_id, "user_id": user_id}, return_json=False)
        if not existing.status or not existing.data:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        workflow = existing.data[0]
        
        # Update only provided fields
        if request.name is not None:
            workflow.name = request.name
        if request.description is not None:
            workflow.description = request.description
        if request.config is not None:
            workflow.config = request.config
        if request.tags is not None:
            workflow.tags = request.tags
        if request.is_active is not None:
            workflow.is_active = request.is_active
        
        updated = db.upsert(workflow, return_json=False)
        return {"status": updated.status, "data": updated.data}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete("/api/workflows/{workflow_id}")
async def delete_workflow(workflow_id: int, user_id: str, db=Depends(get_db)) -> Dict:
    """Delete workflow (soft delete by setting is_active=False)"""
    try:
        # Check if workflow exists and belongs to user
        workflow = db.get(WorkflowDB, filters={"id": workflow_id, "user_id": user_id}, return_json=False)
        if not workflow.status or not workflow.data:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        # Soft delete by setting is_active=False
        workflow_obj = workflow.data[0]
        workflow_obj.is_active = False
        
        result = db.upsert(workflow_obj)
        return {"status": result.status, "message": "Workflow deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/api/workflows/run")
async def create_workflow_run(request: CreateWorkflowRunRequest, db=Depends(get_db)) -> Dict:
    """Create an ephemeral workflow run - returns temporary run_id"""
    try:
        # Generate ephemeral run ID
        run_id = str(uuid.uuid4())
        
        # If workflow_id provided, fetch the workflow config
        if request.workflow_id:
            workflow = db.get(WorkflowDB, filters={"id": request.workflow_id}, return_json=False)
            if not workflow.status or not workflow.data:
                raise HTTPException(status_code=404, detail="Workflow not found")
            
            workflow_config = workflow.data[0].config
        elif request.workflow_config:
            # Use provided inline config
            workflow_config = request.workflow_config
        else:
            raise HTTPException(status_code=400, detail="Either workflow_id or workflow_config must be provided")
        
        # For now, just return the run_id 
        # The actual workflow execution will happen via WebSocket
        return {
            "status": True,
            "data": {
                "run_id": run_id,
                "workflow_config": workflow_config
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# ==================== WebSocket Routes ====================

# Global tracking for ephemeral workflow runs
active_workflow_runs: Dict[str, Dict[str, Any]] = {}


class WorkflowWebSocketManager:
    """Manages WebSocket connections for workflow execution"""
    
    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, run_id: str) -> bool:
        """Connect a WebSocket for a workflow run"""
        try:
            await websocket.accept()
            self.connections[run_id] = websocket
            logger.info(f"Workflow WebSocket connected for run {run_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect workflow WebSocket: {e}")
            return False
    
    async def disconnect(self, run_id: str):
        """Disconnect and cleanup"""
        if run_id in self.connections:
            del self.connections[run_id]
        if run_id in active_workflow_runs:
            del active_workflow_runs[run_id]
        logger.info(f"Workflow WebSocket disconnected for run {run_id}")
    
    async def send_message(self, run_id: str, message: Dict[str, Any]):
        """Send message to connected WebSocket"""
        if run_id in self.connections:
            try:
                await self.connections[run_id].send_json(message)
            except Exception as e:
                logger.error(f"Failed to send message to run {run_id}: {e}")
    
    async def execute_workflow(self, run_id: str, workflow_config: Dict[str, Any], initial_input: Any = None):
        """Execute a workflow and stream progress"""
        try:
            # Create workflow from config
            workflow = Workflow.load_component(workflow_config)
            
            # Create and run workflow runner
            runner = WorkflowRunner()
            
            # Stream workflow execution events
            try:
                async for event in runner.run_stream(workflow, initial_input):
                    # Send the event directly as JSON (with run_id added)
                    event_data = event.model_dump()
                    event_data["run_id"] = run_id  # Add run_id for WebSocket context
                    await self.send_message(run_id, event_data)
                
            except Exception as workflow_error:
                # Send error message for unexpected errors
                await self.send_message(run_id, {
                    "type": "workflow_error",
                    "run_id": run_id,
                    "error": str(workflow_error),
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Workflow execution error for run {run_id}: {e}")
            await self.send_message(run_id, {
                "type": "workflow_error", 
                "run_id": run_id,
                "error": f"Failed to execute workflow: {str(e)}",
                "timestamp": datetime.now().isoformat()
            })


# Global workflow WebSocket manager
workflow_manager = WorkflowWebSocketManager()


@router.websocket("/api/workflow/ws/{run_id}")
async def workflow_websocket(
    websocket: WebSocket,
    run_id: str,
    auth_manager=Depends(get_ws_auth_manager),
):
    """WebSocket endpoint for workflow execution"""
    
    try:
        # Connect websocket
        connected = await workflow_manager.connect(websocket, run_id)
        if not connected:
            return
        
        # Handle authentication if enabled
        if auth_manager is not None:
            ws_auth = WebSocketAuthHandler(auth_manager)
            success, user = await ws_auth.authenticate(websocket)
            if not success:
                logger.warning(f"Authentication failed for workflow WebSocket run {run_id}")
                await websocket.send_json({
                    "type": "error",
                    "error": "Authentication failed",
                    "timestamp": datetime.now().isoformat(),
                })
                return
        
        logger.info(f"Workflow WebSocket connection established for run {run_id}")
        
        # Store run info
        active_workflow_runs[run_id] = {
            "created_at": datetime.now(),
            "status": "connected"
        }
        
        raw_message = None  # Initialize to avoid unbound variable issue
        while True:
            try:
                raw_message = await websocket.receive_text()
                message = json.loads(raw_message)
                
                if message.get("type") == "start":
                    # Handle start message
                    logger.info(f"Received workflow start request for run {run_id}")
                    
                    workflow_config = message.get("workflow_config")
                    initial_input = message.get("input")
                    
                    if not workflow_config:
                        await websocket.send_json({
                            "type": "error",
                            "error": "workflow_config is required",
                            "timestamp": datetime.now().isoformat(),
                        })
                        continue
                    
                    # Start workflow execution in background
                    asyncio.create_task(
                        workflow_manager.execute_workflow(run_id, workflow_config, initial_input)
                    )
                
                elif message.get("type") == "stop":
                    logger.info(f"Received workflow stop request for run {run_id}")
                    # TODO: Implement workflow cancellation
                    await websocket.send_json({
                        "type": "workflow_stopped",
                        "run_id": run_id,
                        "timestamp": datetime.now().isoformat(),
                    })
                    break
                
                elif message.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong", 
                        "timestamp": datetime.now().isoformat()
                    })
                
                else:
                    logger.warning(f"Unknown message type: {message.get('type')}")
                    
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received: {raw_message or 'None'}")
                await websocket.send_json({
                    "type": "error", 
                    "error": "Invalid message format", 
                    "timestamp": datetime.now().isoformat()
                })
    
    except WebSocketDisconnect:
        logger.info(f"Workflow WebSocket disconnected for run {run_id}")
    except Exception as e:
        logger.error(f"Workflow WebSocket error: {str(e)}")
    finally:
        await workflow_manager.disconnect(run_id)


@router.get("/api/workflow/ws/status/{run_id}")
async def get_workflow_run_status(run_id: str):
    """Get status of an active workflow run"""
    if run_id not in active_workflow_runs:
        return {"status": False, "message": "Run not found"}
    
    run_info = active_workflow_runs[run_id]
    return {
        "status": True,
        "data": {
            "run_id": run_id,
            "created_at": run_info["created_at"].isoformat(),
            "status": run_info["status"]
        }
    }
