# AutoGen Python packages

See [`autogen-core`](./packages/autogen-core/) package for main functionality.


## Development

**TL;DR**, run all checks with:

```sh
uv sync
source .venv/bin/activate
poe check
```

### Setup

- [Install `uv`](https://docs.astral.sh/uv/getting-started/installation/).

### Virtual environment

To get a shell with the package available (virtual environment),
in the current directory,
run:

```sh
uv sync
source .venv/bin/activate
```

### Common tasks

- Format: `poe format`
- Lint: `poe lint`
- Test: `poe test`
- Mypy: `poe mypy`
- Pyright: `poe pyright`
- Build docs: `poe --directory ./packages/autogen-core/ docs-build`
- Auto rebuild+serve docs: `poe --directory ./packages/autogen-core/ docs-serve`

> [!NOTE]
> These need to be run in the virtual environment.


### Create new package

To create a new package, run:

```sh
uv sync
source .venv/bin/activate
cookiecutter ./templates/new-package/
```
