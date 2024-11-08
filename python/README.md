# AutoGen Python packages

See [`autogen-core`](./packages/autogen-core/) package for main functionality.


## Development

**TL;DR**, run all checks with:

```sh
uv sync --all-extras
source .venv/bin/activate
poe check
```

### Setup
`uv` is a package manager that assists in creating the necessary environment and installing packages to run AutoGen.
- [Install `uv`](https://docs.astral.sh/uv/getting-started/installation/).

### Virtual Environment
During development, you may need to test changes made to any of the packages.\
To do so, create a virtual environment where the AutoGen packages are installed based on the current state of the directory.\
Run the following commands at the root level of the Python directory:

```sh
uv sync --all-extras
source .venv/bin/activate
```
- `uv sync --all-extras` will create a `.venv` directory at the current level and install packages from the current directory along with any other dependencies. The `all-extras` flag adds optional dependencies.
- `source .venv/bin/activate` activates the virtual environment.

### Common Tasks
To create a pull request (PR), ensure the following checks are met. You can run each check individually:
- Format: `poe format`
- Lint: `poe lint`
- Test: `poe test`
- Mypy: `poe mypy`
- Pyright: `poe pyright`
- Build docs: `poe --directory ./packages/autogen-core/ docs-build`
- Auto rebuild+serve docs: `poe --directory ./packages/autogen-core/ docs-serve`
Alternatively, you can run all the checks with:
- `poe check`

> [!NOTE]
> These need to be run in the virtual environment.

### Creating a New Package

To create a new package, similar to `autogen-core` or `autogen-chat`, use the following:

```sh
uv sync
source .venv/bin/activate
cookiecutter ./templates/new-package/
```
