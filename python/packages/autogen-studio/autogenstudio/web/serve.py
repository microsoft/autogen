import os

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any

from ..datamodel import Response
from ..teammanager import TeamManager

app = FastAPI()
team_manager = TeamManager()


@app.get("/predict/{task}")
async def predict(task: str):
    response = Response(message="Task successfully completed", status=True, data=None)
    try:
        team_file_path = os.environ.get("AUTOGENSTUDIO_TEAM_FILE")

        # Check if team_file_path is set
        if team_file_path is None:
            raise ValueError("AUTOGENSTUDIO_TEAM_FILE environment variable is not set")

        result_message = await team_manager.run(task=task, team_config=team_file_path)
        response.data = force_model_dump(result_message)
    except Exception as e:
        response.message = str(e)
        response.status = False
    return response

def force_model_dump(obj: Any) -> Any:
    """
    Force dump all fields of a Pydantic BaseModel, even when inherited
    from ABCs as BaseAgentEvent and BaseChatMessage.
    """
    if isinstance(obj, BaseModel):
        output = {}
        for name, _field in obj.__fields__.items():
            value = getattr(obj, name)
            output[name] = force_model_dump(value)
        return output
    elif isinstance(obj, list):
        return [force_model_dump(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: force_model_dump(v) for k, v in obj.items()}
    else:
        return obj