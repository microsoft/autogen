import os
from typing_extensions import Annotated
import typer
import uvicorn

from .version import VERSION
from .utils.dbutils import DBManager

app = typer.Typer()


@app.command()
def ui(
    host: str = "127.0.0.1",
    port: int = 8081,
    workers: int = 1,
    reload: Annotated[bool, typer.Option("--reload")] = False,
    docs: bool = False,
    appdir: str = None,
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
    """

    os.environ["AUTOGENSTUDIO_API_DOCS"] = str(docs)
    if appdir:
        os.environ["AUTOGENSTUDIO_APPDIR"] = appdir

    uvicorn.run(
        "autogenstudio.web.app:app",
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
