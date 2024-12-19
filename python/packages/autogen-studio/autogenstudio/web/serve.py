# loads a fast api api endpoint with a single endpoint that takes text query and return a response

import json
import os

from fastapi import FastAPI

from ..datamodel import Response
from ..teammanager import TeamManager

app = FastAPI()
team_file_path = os.environ.get("AUTOGENSTUDIO_TEAM_FILE", None)


if team_file_path:
    team_manager = TeamManager()
else:
    raise ValueError("Team file must be specified")


@app.get("/predict/{task}")
async def predict(task: str):
    response = Response(message="Task successfully completed", status=True, data=None)
    try:
        result_message = await team_manager.run(task=task, team_config=team_file_path)
        response.data = result_message
    except Exception as e:
        response.message = str(e)
        response.status = False
    return response
