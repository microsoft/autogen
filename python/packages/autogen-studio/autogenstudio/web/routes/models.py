# api/routes/models.py
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict
from openai import OpenAIError
from ..deps import get_db
from ...datamodel import Model
from ...utils import test_model

router = APIRouter()


@router.get("/")
async def list_models(
    user_id: str,
    db=Depends(get_db)
) -> Dict:
    """List all models for a user"""
    response = db.get(Model, filters={"user_id": user_id})
    return {
        "status": True,
        "data": response.data
    }


@router.get("/{model_id}")
async def get_model(
    model_id: int,
    user_id: str,
    db=Depends(get_db)
) -> Dict:
    """Get a specific model"""
    response = db.get(
        Model,
        filters={"id": model_id, "user_id": user_id}
    )
    if not response.status or not response.data:
        raise HTTPException(status_code=404, detail="Model not found")
    return {
        "status": True,
        "data": response.data[0]
    }


@router.post("/")
async def create_model(
    model: Model,
    db=Depends(get_db)
) -> Dict:
    """Create a new model"""
    response = db.upsert(model)
    if not response.status:
        raise HTTPException(status_code=400, detail=response.message)
    return {
        "status": True,
        "data": response.data
    }


@router.delete("/{model_id}")
async def delete_model(
    model_id: int,
    user_id: str,
    db=Depends(get_db)
) -> Dict:
    """Delete a model"""
    response = db.delete(
        filters={"id": model_id, "user_id": user_id},
        model_class=Model
    )
    return {
        "status": True,
        "message": "Model deleted successfully"
    }


@router.post("/test")
async def test_model_endpoint(model: Model) -> Dict:
    """Test a model configuration"""
    try:
        response = test_model(model)
        return {
            "status": True,
            "message": "Model tested successfully",
            "data": response
        }
    except OpenAIError as e:
        raise HTTPException(
            status_code=400,
            detail=f"OpenAI API error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error testing model: {str(e)}"
        )
