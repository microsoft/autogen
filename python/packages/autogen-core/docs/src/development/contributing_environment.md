# Setup Local Development Environment

## Create a fork of AutoGen
You will need your own copy of AutoGen (aka fork) to work on the code. Go to the AutoGen [project page](https://github.com/microsoft/autogen) and hit the Fork button. You will want to clone your fork to your machine

```sh
git clone https://github.com/your-user-name/autogen.git autogen-yourname
cd autogen-yourname
git remote add upstream https://github.com/microsoft/autogen.git
git fetch upstream
```

This creates the directory autogen-yourname and connects your repository to the upstream (main project) AutoGen repository.

## Install uv
`uv` is a package manager that assists in creating the necessary environment and installing packages to run AutoGen.

You can install it with `pipx install uv` or `pip install uv`, or other [installation methods](https://docs.astral.sh/uv/getting-started/installation/).

## Create a Virtual Environment
During development, you may need to test changes made to any of the packages.\
To do so, create a virtual environment where the AutoGen packages are installed based on the current state of the directory.\
Run the following commands at the root level of the `python` directory, i.e., `autogen-yourname/python`:

```sh
uv sync --all-extras
source .venv/bin/activate
```
- `uv sync --all-extras` will create a `.venv` directory at the current level and install packages from the current directory along with any other dependencies. The `all-extras` flag adds optional dependencies.
- `source .venv/bin/activate` activates the virtual environment.

## Common Tasks before making a PR
To create a pull request (PR), ensure the following checks are met. You can run each check individually:
- Format: `poe format`
- Lint: `poe lint`
- Test: `poe test`
- Mypy: `poe mypy`
- Pyright: `poe pyright`
- Proto: `poe gen-proto`
- Clean and Build docs: `poe doc-clean && poe doc-build`
- Auto rebuild+serve docs: `poe docs-serve`

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
