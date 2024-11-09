import os
from typing import Optional

import typer
import uvicorn
from typing_extensions import Annotated

from .version import VERSION

app = typer.Typer()


@app.command()
def ui(
    host: str = "127.0.0.1",
    port: int = 8081,
    workers: int = 1,
    reload: Annotated[bool, typer.Option("--reload")] = True,
    docs: bool = True,
    appdir: str = None,
    database_uri: Optional[str] = None,
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
        database-uri (str, optional): Database URI to connect to. Defaults to None.
    """

    os.environ["AUTOGENSTUDIO_API_DOCS"] = str(docs)
    if appdir:
        os.environ["AUTOGENSTUDIO_APPDIR"] = appdir
    if database_uri:
        os.environ["AUTOGENSTUDIO_DATABASE_URI"] = database_uri
    if upgrade_database:
        os.environ["AUTOGENSTUDIO_UPGRADE_DATABASE"] = "1"

    uvicorn.run(
        "autogenstudio.web.app:app",
        host=host,
        port=port,
        workers=workers,
        reload=reload,
        reload_excludes=[
            "**/alembic/*",
            "**/alembic.ini",
            "**/versions/*"
        ] if reload else None
    )


@app.command()
def serve(
    workflow: str = "",
    host: str = "127.0.0.1",
    port: int = 8084,
    workers: int = 1,
    docs: bool = False,
):
    """
    Serve an API Endpoint based on an AutoGen Studio workflow json file.

    Args:
        workflow (str): Path to the workflow json file.
        host (str, optional): Host to run the UI on. Defaults to 127.0.0.1 (localhost).
        port (int, optional): Port to run the UI on. Defaults to 8081.
        workers (int, optional): Number of workers to run the UI with. Defaults to 1.
        reload (bool, optional): Whether to reload the UI on code changes. Defaults to False.
        docs (bool, optional): Whether to generate API docs. Defaults to False.

    """

    os.environ["AUTOGENSTUDIO_API_DOCS"] = str(docs)
    os.environ["AUTOGENSTUDIO_WORKFLOW_FILE"] = workflow

    uvicorn.run(
        "autogenstudio.web.serve:app",
        host=host,
        port=port,
        workers=workers,
        reload=False,
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
