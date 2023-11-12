from typing_extensions import Annotated
import typer
import uvicorn
import os

app = typer.Typer(invoke_without_command=True)


@app.callback()
def main(
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
def models():
    print("A list of supported providers:")


def run():
    app()


if __name__ == "__main__":
    app()
