# api/routes/settings.py
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException

from ...datamodel import Settings, SettingsConfig
from ..deps import get_db

router = APIRouter()


@router.get("/")
async def get_settings(user_id: str, db=Depends(get_db)) -> Dict:
    try:
        response = db.get(Settings, filters={"user_id": user_id})
        if not response.status or not response.data:
            # create a default settings
            config = SettingsConfig(environment=[])
            default_settings = Settings(user_id=user_id, config=config.model_dump())
            db.upsert(default_settings)
            response = db.get(Settings, filters={"user_id": user_id})
        return {"status": True, "data": response.data[0]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/")
async def update_settings(settings: Settings, db=Depends(get_db)) -> Dict:
    response = db.upsert(settings)
    if not response.status:
        raise HTTPException(status_code=400, detail=response.message)
    return {"status": True, "data": response.data}
