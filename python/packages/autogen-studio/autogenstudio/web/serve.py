import os

from fastapi import FastAPI

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
        response.data = result_message
    except Exception as e:
        response.message = str(e)
        response.status = False
    return response
