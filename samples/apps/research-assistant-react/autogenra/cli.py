import os
from typing_extensions import Annotated
import typer
import uvicorn

from .version import VERSION

app = typer.Typer()


@app.command()
def ui(
    host: str = "127.0.0.1",
    port: int = 8081,
    workers: int = 1,
    reload: Annotated[bool, typer.Option("--reload")] = False,
    docs: bool = False,
):
    """
    Launch the Autogen RA UI CLI .Pass in parameters host, port, workers, and reload to override the default values.
    """

    os.environ["AUTOGENUI_API_DOCS"] = str(docs)

    uvicorn.run(
        "autogenra.web.app:app",
        host=host,
        port=port,
        workers=workers,
        reload=reload,
    )


@app.command()
def version():
    """
    Print the version of the Autogen RA UI CLI.
    """

    typer.echo(f"Autogen RA UI CLI version: {VERSION}")


def run():
    app()


if __name__ == "__main__":
    app()
