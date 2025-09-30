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


@app.get("/predict_team/{team}/{task}")
async def predict_team(team: str, task: str):
    response = Response(message="Task successfully completed", status=True, data=None)
    try:
        team_folder_path = os.environ.get("AUTOGENSTUDIO_TEAM_FOLDER")

        if team_folder_path is None:
            raise ValueError("AUTOGENSTUDIO_TEAM_FOLDER environment variable is not set")

        if not os.path.isdir(team_folder_path):
            raise ValueError("Team folder not found.")

        team_files = {}
        for f in os.listdir(team_folder_path):
            if os.path.isfile(os.path.join(team_folder_path, f)):
                filename = f.split(".")[0]
                team_files[filename] = os.path.join(team_folder_path, f)

        if not team_files:
            raise ValueError("No files found in team folder path.")

        if team not in team_files:
            raise ValueError(f"Team {team} not found in team folder path.")

        team_file_path = team_files[team]
        result_message = await team_manager.run(task=task, team_config=team_file_path)
        response.data = result_message
    except Exception as e:
        response.message = str(e)
        response.status = False
    return response
