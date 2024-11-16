# api/routes/sessions.py
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict
from ..deps import get_db
from ...datamodel import Session, Message

router = APIRouter()


@router.get("/")
async def list_sessions(
    user_id: str,
    db=Depends(get_db)
) -> Dict:
    """List all sessions for a user"""
    response = db.get(Session, filters={"user_id": user_id})
    return {
        "status": True,
        "data": response.data
    }


@router.get("/{session_id}")
async def get_session(
    session_id: int,
    user_id: str,
    db=Depends(get_db)
) -> Dict:
    """Get a specific session"""
    response = db.get(
        Session,
        filters={"id": session_id, "user_id": user_id}
    )
    if not response.status or not response.data:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "status": True,
        "data": response.data[0]
    }


@router.post("/")
async def create_session(
    session: Session,
    db=Depends(get_db)
) -> Dict:
    """Create a new session"""
    response = db.upsert(session)
    if not response.status:
        raise HTTPException(status_code=400, detail=response.message)
    return {
        "status": True,
        "data": response.data
    }


@router.put("/{session_id}")
async def update_session(
    session_id: int,
    user_id: str,
    session: Session,
    db=Depends(get_db)
) -> Dict:
    """Update an existing session"""
    # First verify the session belongs to user
    existing = db.get(
        Session,
        filters={"id": session_id, "user_id": user_id}
    )
    if not existing.status or not existing.data:
        raise HTTPException(status_code=404, detail="Session not found")

    # Update the session
    response = db.upsert(session)
    if not response.status:
        raise HTTPException(status_code=400, detail=response.message)

    return {
        "status": True,
        "data": response.data,
        "message": "Session updated successfully"
    }


@router.delete("/{session_id}")
async def delete_session(
    session_id: int,
    user_id: str,
    db=Depends(get_db)
) -> Dict:
    """Delete a session"""
    response = db.delete(
        filters={"id": session_id, "user_id": user_id},
        model_class=Session
    )
    return {
        "status": True,
        "message": "Session deleted successfully"
    }


@router.get("/{session_id}/messages")
async def list_messages(
    session_id: int,
    user_id: str,
    db=Depends(get_db)
) -> Dict:
    """List all messages for a session"""
    filters = {"session_id": session_id, "user_id": user_id}
    response = db.get(Message, filters=filters, order="asc")
    return {
        "status": True,
        "data": response.data
    }
