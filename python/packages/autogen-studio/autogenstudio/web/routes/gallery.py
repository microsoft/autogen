# api/routes/gallery.py
from fastapi import APIRouter, Depends, HTTPException

from ...database import DatabaseManager
from ...datamodel import Gallery, GalleryConfig, Response, Run, Session
from ..deps import get_db

router = APIRouter()


@router.post("/")
async def create_gallery_entry(
    gallery_data: GalleryConfig, user_id: str, db: DatabaseManager = Depends(get_db)
) -> Response:
    # First validate that user owns all runs
    for run in gallery_data.runs:
        run_result = db.get(Run, filters={"id": run.id})
        if not run_result.status or not run_result.data:
            raise HTTPException(status_code=404, detail=f"Run {run.id} not found")

        # Get associated session to check ownership
        session_result = db.get(Session, filters={"id": run_result.data[0].session_id})
        if not session_result.status or not session_result.data or session_result.data[0].user_id != user_id:
            raise HTTPException(status_code=403, detail=f"Not authorized to add run {run.id} to gallery")

    # Create gallery entry
    gallery = Gallery(user_id=user_id, config=gallery_data)
    result = db.upsert(gallery)
    return result


@router.get("/{gallery_id}")
async def get_gallery_entry(gallery_id: int, user_id: str, db: DatabaseManager = Depends(get_db)) -> Response:
    result = db.get(Gallery, filters={"id": gallery_id})
    if not result.status or not result.data:
        raise HTTPException(status_code=404, detail="Gallery entry not found")

    gallery = result.data[0]
    if gallery.config["visibility"] != "public" and gallery.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this gallery entry")

    return result


@router.get("/")
async def list_gallery_entries(user_id: str, db: DatabaseManager = Depends(get_db)) -> Response:
    result = db.get(Gallery, filters={"user_id": user_id})
    return result


@router.delete("/{gallery_id}")
async def delete_gallery_entry(gallery_id: int, user_id: str, db: DatabaseManager = Depends(get_db)) -> Response:
    # Check ownership first
    result = db.get(Gallery, filters={"id": gallery_id})
    if not result.status or not result.data:
        raise HTTPException(status_code=404, detail="Gallery entry not found")

    if result.data[0].user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this gallery entry")

    # Delete if authorized
    return db.delete(Gallery, filters={"id": gallery_id})
