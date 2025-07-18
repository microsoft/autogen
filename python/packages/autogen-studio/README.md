# AutoGen Studio

[![PyPI version](https://badge.fury.io/py/autogenstudio.svg)](https://badge.fury.io/py/autogenstudio)
![PyPI - Downloads](https://img.shields.io/pypi/dm/autogenstudio)

![ARA](https://media.githubusercontent.com/media/microsoft/autogen/refs/heads/main/python/packages/autogen-studio/docs/ags_screen.png)

AutoGen Studio is an AutoGen-powered AI app (user interface) to help you rapidly prototype AI agents, enhance them with skills, compose them into workflows and interact with them to accomplish tasks. It is built on top of the [AutoGen](https://microsoft.github.io/autogen) framework, which is a toolkit for building AI agents.

Code for AutoGen Studio is on GitHub at [microsoft/autogen](https://github.com/microsoft/autogen/tree/main/python/packages/autogen-studio)

> [!WARNING]
> AutoGen Studio is under active development and is currently not meant to be a production-ready app. Expect breaking changes in upcoming releases. [Documentation](https://microsoft.github.io/autogen/docs/autogen-studio/getting-started) and the `README.md` might be outdated.

## Updates

- **2024-11-14:** AutoGen Studio is being rewritten to use the updated AutoGen 0.4.0 api AgentChat api.
- **2024-04-17:** April 17: AutoGen Studio database layer is now rewritten to use [SQLModel](https://sqlmodel.tiangolo.com/) (Pydantic + SQLAlchemy). This provides entity linking (skills, models, agents and workflows are linked via association tables) and supports multiple [database backend dialects](https://docs.sqlalchemy.org/en/20/dialects/) supported in SQLAlchemy (SQLite, PostgreSQL, MySQL, Oracle, Microsoft SQL Server). The backend database can be specified a `--database-uri` argument when running the application. For example, `autogenstudio ui --database-uri sqlite:///database.sqlite` for SQLite and `autogenstudio ui --database-uri postgresql+psycopg://user:password@localhost/dbname` for PostgreSQL.
- **2024-03-12:** Default directory for AutoGen Studio is now /home/\<USER\>/.autogenstudio. You can also specify this directory using the `--appdir` argument when running the application. For example, `autogenstudio ui --appdir /path/to/folder`. This will store the database and other files in the specified directory e.g. `/path/to/folder/database.sqlite`. `.env` files in that directory will be used to set environment variables for the app.

## Project Structure:

- `autogenstudio/` contains code for the backend classes and web api (FastAPI)
- `frontend/` contains code for the webui, built with Gatsby and TailwindCSS

## Installation

There are two ways to install AutoGen Studio - from PyPi or from the source. We **recommend installing from PyPi** unless you plan to modify the source code.

### Install from PyPi (Recommended)

We recommend using a virtual environment (e.g., venv) to avoid conflicts with existing Python packages. With Python 3.10 or newer active in your virtual environment, use pip to install AutoGen Studio:

```bash
pip install -U autogenstudio
```

### Install from source

_Note: This approach requires some familiarity with building interfaces in React._

### Important: Git LFS Requirement

AutoGen Studio uses Git Large File Storage (LFS) for managing image and other large files. If you clone the repository without git-lfs, you'll encounter build errors related to image formats.

**Before cloning the repository:**

1. Install git-lfs:

   ```bash
   # On Debian/Ubuntu
   apt-get install git-lfs

   # On macOS with Homebrew
   brew install git-lfs

   # On Windows with Chocolatey
   choco install git-lfs
   ```

2. Set up git-lfs:
   ```bash
   git lfs install
   ```

**If you've already cloned the repository:**

```bash
git lfs install
git lfs fetch --all
git lfs checkout  # downloads all missing image files to the working directory
```

This setup is handled automatically if you use the dev container method of installation.

You have two options for installing from source: manually or using a dev container.

#### A) Install from source manually

1. Ensure you have Python 3.10+ and Node.js (version above 14.15.0) installed.
2. Clone the AutoGen Studio repository and install its Python dependencies using `pip install -e .`
3. Navigate to the `python/packages/autogen-studio/frontend` directory, install the dependencies, and build the UI:

   ```bash
   npm install -g gatsby-cli
   npm install --global yarn
   cd frontend
   yarn install
   yarn build
   # Windows users may need alternative commands to build the frontend:
   gatsby clean && rmdir /s /q ..\\autogenstudio\\web\\ui 2>nul & (set \"PREFIX_PATH_VALUE=\" || ver>nul) && gatsby build --prefix-paths && xcopy /E /I /Y public ..\\autogenstudio\\web\\ui
   ```

#### B) Install from source using a dev container

1. Follow the [Dev Containers tutorial](https://code.visualstudio.com/docs/devcontainers/tutorial) to install VS Code, Docker and relevant extensions.
2. Clone the AutoGen Studio repository.
3. Open `python/packages/autogen-studio/`in VS Code. Click the blue button in bottom the corner or press F1 and select _"Dev Containers: Reopen in Container"_.
4. Build the UI:

   ```bash
   cd frontend
   yarn build
   ```

### Running the Application

Once installed, run the web UI by entering the following in your terminal:

```bash
autogenstudio ui --port 8081
```

This command will start the application on the specified port. Open your web browser and go to <http://localhost:8081/> to use AutoGen Studio.

AutoGen Studio also takes several parameters to customize the application:

- `--host <host>` argument to specify the host address. By default, it is set to `localhost`.
- `--appdir <appdir>` argument to specify the directory where the app files (e.g., database and generated user files) are stored. By default, it is set to the `.autogenstudio` directory in the user's home directory.
- `--port <port>` argument to specify the port number. By default, it is set to `8080`.
- `--reload` argument to enable auto-reloading of the server when changes are made to the code. By default, it is set to `False`.
- `--database-uri` argument to specify the database URI. Example values include `sqlite:///database.sqlite` for SQLite and `postgresql+psycopg://user:password@localhost/dbname` for PostgreSQL. If this is not specified, the database URL defaults to a `database.sqlite` file in the `--appdir` directory.
- `--upgrade-database` argument to upgrade the database schema to the latest version. By default, it is set to `False`.

Now that you have AutoGen Studio installed and running, you are ready to explore its capabilities, including defining and modifying agent workflows, interacting with agents and sessions, and expanding agent skills.

## AutoGen Studio Lite

AutoGen Studio Lite provides a lightweight way to quickly prototype and experiment with AI agent teams. It's designed for rapid experimentation without the full database setup.

### CLI Usage

Launch Studio Lite from the command line:

```bash
# Quick start with default team
autogenstudio lite

# Use custom team file
autogenstudio lite --team ./my_team.json --port 8080

# Custom session name
autogenstudio lite --session-name "My Experiment" --auto-open
```

### Programmatic Usage

Use Studio Lite directly in your Python code:

```python
from autogenstudio.lite import LiteStudio

# Quick start with default team
studio = LiteStudio()
# Use with AutoGen team objects
from autogen_agentchat.teams import RoundRobinGroupChat
team = RoundRobinGroupChat([agent1, agent2], termination_condition=...)

# Context manager usage
with LiteStudio(team=team) as studio:
    # Studio runs in background
    # Do other work here
    pass
```

#### Local frontend development server

See `./frontend/README.md`

## Contribution Guide

We welcome contributions to AutoGen Studio. We recommend the following general steps to contribute to the project:

- Review the overall AutoGen project [contribution guide](https://github.com/microsoft/autogen?tab=readme-ov-file#contributing)
- Please review the AutoGen Studio [roadmap](https://github.com/microsoft/autogen/issues/4006) to get a sense of the current priorities for the project. Help is appreciated especially with Studio issues tagged with `help-wanted`
- Please initiate a discussion on the roadmap issue or a new issue to discuss your proposed contribution.
- Submit a pull request with your contribution!
- If you are modifying AutoGen Studio, it has its own devcontainer. See instructions in `.devcontainer/README.md` to use it
- Please use the tag `proj-studio` for any issues, questions, and PRs related to Studio

## FAQ

Please refer to the AutoGen Studio [FAQs](https://microsoft.github.io/autogen/docs/autogen-studio/faqs) page for more information.

## Acknowledgements

AutoGen Studio is Based on the [AutoGen](https://microsoft.github.io/autogen) project. It was adapted from a research prototype built in October 2023 (original credits: Gagan Bansal, Adam Fourney, Victor Dibia, Piali Choudhury, Saleema Amershi, Ahmed Awadallah, Chi Wang).
