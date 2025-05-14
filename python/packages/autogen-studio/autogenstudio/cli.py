import os
import warnings
from typing import Optional

import typer
import uvicorn
from typing_extensions import Annotated

from .version import VERSION

app = typer.Typer()

# Ignore deprecation warnings from websockets
warnings.filterwarnings("ignore", message="websockets.legacy is deprecated*")
warnings.filterwarnings("ignore", message="websockets.server.WebSocketServerProtocol is deprecated*")


def get_env_file_path():
    app_dir = os.path.join(os.path.expanduser("~"), ".autogenstudio")
    if not os.path.exists(app_dir):
        os.makedirs(app_dir, exist_ok=True)
    return os.path.join(app_dir, "temp_env_vars.env")


@app.command()
def ui(
    host: str = "127.0.0.1",
    port: int = 8081,
    workers: int = 1,
    reload: Annotated[bool, typer.Option("--reload")] = False,
    docs: bool = True,
    appdir: str | None = None,
    database_uri: Optional[str] = None,
    auth_config: Optional[str] = None,
    upgrade_database: bool = False,
):
    """
    Run the AutoGen Studio UI.

    Args:
        host (str, optional): Host to run the UI on. Defaults to 127.0.0.1 (localhost).
        port (int, optional): Port to run the UI on. Defaults to 8081.
        workers (int, optional): Number of workers to run the UI with. Defaults to 1.
        reload (bool, optional): Whether to reload the UI on code changes. Defaults to False.
        docs (bool, optional): Whether to generate API docs. Defaults to False.
        appdir (str, optional): Path to the AutoGen Studio app directory. Defaults to None.
        database_uri (str, optional): Database URI to connect to. Defaults to None.
        auth_config (str, optional): Path to authentication configuration YAML. Defaults to None.
        upgrade_database (bool, optional): Whether to upgrade the database. Defaults to False.
    """
    # Write configuration
    env_vars = {
        "AUTOGENSTUDIO_HOST": host,
        "AUTOGENSTUDIO_PORT": port,
        "AUTOGENSTUDIO_API_DOCS": str(docs),
    }

    if appdir:
        env_vars["AUTOGENSTUDIO_APPDIR"] = appdir
    if database_uri:
        env_vars["AUTOGENSTUDIO_DATABASE_URI"] = database_uri
    if auth_config:
        if not os.path.exists(auth_config):
            typer.echo(f"Error: Auth config file not found: {auth_config}", err=True)
            raise typer.Exit(1)
        env_vars["AUTOGENSTUDIO_AUTH_CONFIG"] = auth_config
    if upgrade_database:
        env_vars["AUTOGENSTUDIO_UPGRADE_DATABASE"] = "1"

    # Create temporary env file to share configuration with uvicorn workers
    env_file_path = get_env_file_path()
    with open(env_file_path, "w") as temp_env:
        for key, value in env_vars.items():
            temp_env.write(f"{key}={value}\n")

    uvicorn.run(
        "autogenstudio.web.app:app",
        host=host,
        port=port,
        workers=workers,
        reload=reload,
        reload_excludes=["**/alembic/*", "**/alembic.ini", "**/versions/*"] if reload else None,
        env_file=env_file_path,
    )


@app.command()
def serve(
    team: str = "",
    teamfolder: str = "",
    host: str = "127.0.0.1",
    port: int = 8084,
    workers: int = 1,
    reload: Annotated[bool, typer.Option("--reload")] = False,
    docs: bool = False,
):
    """
    Serve an API Endpoint based on an AutoGen Studio workflow json file.

    Args:
        team (str): Path to the team json file.
        teamfolder (str): Path to folder containing team json files (team or teamfolder is required).
        host (str, optional): Host to run the UI on. Defaults to 127.0.0.1 (localhost).
        port (int, optional): Port to run the UI on. Defaults to 8084
        workers (int, optional): Number of workers to run the UI with. Defaults to 1.
        reload (bool, optional): Whether to reload the UI on code changes. Defaults to False.
        docs (bool, optional): Whether to generate API docs. Defaults to False.

    """

    os.environ["AUTOGENSTUDIO_API_DOCS"] = str(docs)
    os.environ["AUTOGENSTUDIO_TEAM_FILE"] = team
    os.environ["AUTOGENSTUDIO_TEAM_FOLDER"] = teamfolder

    if not team and not teamfolder:
        raise ValueError("Team file or folder is required.")
    if team and not os.path.exists(team):
        raise ValueError(f"Team file {team} not found.")
    if teamfolder and not os.path.exists(teamfolder):
        raise ValueError(f"Team folder {teamfolder} not found.")

    uvicorn.run(
        "autogenstudio.web.serve:app",
        host=host,
        port=port,
        workers=workers,
        reload=reload,
    )


@app.command()
def version():
    """
    Print the version of the AutoGen Studio UI CLI.
    """

    typer.echo(f"AutoGen Studio  CLI version: {VERSION}")


def run():
    app()


if __name__ == "__main__":
    app()
