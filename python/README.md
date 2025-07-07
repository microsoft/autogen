# AutoGen Python packages

[![0.4 Docs](https://img.shields.io/badge/Docs-0.4-blue)](https://microsoft.github.io/autogen/dev/)
[![PyPi autogen-core](https://img.shields.io/badge/PyPi-autogen--core-blue?logo=pypi)](https://pypi.org/project/autogen-core/) [![PyPi autogen-agentchat](https://img.shields.io/badge/PyPi-autogen--agentchat-blue?logo=pypi)](https://pypi.org/project/autogen-agentchat/) [![PyPi autogen-ext](https://img.shields.io/badge/PyPi-autogen--ext-blue?logo=pypi)](https://pypi.org/project/autogen-ext/)

This directory works as a single `uv` workspace containing all project packages. See [`packages`](./packages/) to discover all project packages.

## Migrating from 0.2.x?

Please refer to the [migration guide](./migration_guide.md) for how to migrate your code from 0.2.x to 0.4.x.

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

To upgrade `uv` to the latest version, run:

```sh
uv self update
```

<!-- **Note:** To prevent incompatibilities between versions the same UV version as is running in CI should be used. Check the version in CI by looking the `setup-uv` action, [here](https://github.com/microsoft/autogen/blob/main/.github/workflows/checks.yml#L40) for example.

For example, to change your version to `0.5.18`, run:
```sh
uv self update 0.5.18
``` -->

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
- Build docs: `poe docs-build`
- Check docs: `poe docs-check`
- Clean docs: `poe docs-clean`
- Check code blocks in API references: `poe docs-check-examples`
- Auto rebuild+serve docs: `poe docs-serve`
- Check samples in `python/samples`: `poe samples-code-check`
  Alternatively, you can run all the checks with:
- `poe check`

> [!NOTE]
> These need to be run in the virtual environment.

### Syncing Dependencies

When you pull new changes, you may need to update the dependencies.
To do so, first make sure you are in the virtual environment, and then in the `python` directory, run:

```sh
uv sync --all-extras
```

This will update the dependencies in the virtual environment.

### Creating a New Package

To create a new package, similar to `autogen-core` or `autogen-chat`, use the following:

```sh
uv sync --python 3.12
source .venv/bin/activate
cookiecutter ./templates/new-package/
```
