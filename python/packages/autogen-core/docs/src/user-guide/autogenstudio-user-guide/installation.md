---
myst:
  html_meta:
    "description lang=en": |
      User Guide for AutoGen Studio - A low code tool for building and debugging multi-agent systems
---

# Installation

There are two ways to install AutoGen Studio - from PyPi or from source. We **recommend installing from PyPi** unless you plan to modify the source code.

1.  **Install from PyPi**

    We recommend using a virtual environment (e.g., conda) to avoid conflicts with existing Python packages. With Python 3.10 or newer active in your virtual environment, use pip to install AutoGen Studio:

    ```bash
    pip install -U autogenstudio
    ```

2.  **Install from Source**

    > Note: This approach requires some familiarity with building interfaces in React.

    If you prefer to install from source, ensure you have Python 3.10+ and Node.js (version above 14.15.0) installed. Here's how you get started:

    - Clone the AutoGen Studio repository and install its Python dependencies:

      ```bash
      pip install -e .
      ```

    - Navigate to the `samples/apps/autogen-studio/frontend` directory, install dependencies, and build the UI:

      ```bash
      npm install -g gatsby-cli
      npm install --global yarn
      cd frontend
      yarn install
      yarn build
      ```

For Windows users, to build the frontend, you may need alternative commands to build the frontend.

```bash

  gatsby clean && rmdir /s /q ..\\autogenstudio\\web\\ui 2>nul & (set \"PREFIX_PATH_VALUE=\" || ver>nul) && gatsby build --prefix-paths && xcopy /E /I /Y public ..\\autogenstudio\\web\\ui

```

### Running the Application

Once installed, run the web UI by entering the following in a terminal:

```bash
autogenstudio ui --port 8081 --appdir /path/to/folder
```

This will start the application on the specified port. Open your web browser and go to `http://localhost:8081/` to begin using AutoGen Studio.

AutoGen Studio also takes several parameters to customize the application:

- `--host <host>` argument to specify the host address. By default, it is set to `localhost`.
- `--appdir <appdir>` argument to specify the directory where the app files (e.g., database and generated user files) are stored. By default, it is set to the a `.autogenstudio` directory in the user's home directory.
- `--port <port>` argument to specify the port number. By default, it is set to `8080`.
- `--upgrade-database` argument to upgrade the database schema (assuming there are changes in the version you are installing). By default, it is set to `False`.
- `--reload` argument to enable auto-reloading of the server when changes are made to the code. By default, it is set to `False`.
- `--database-uri` argument to specify the database URI. Example values include `sqlite:///database.sqlite` for SQLite and `postgresql+psycopg://user:password@localhost/dbname` for PostgreSQL. If this is not specified, the database URI defaults to a `database.sqlite` file in the `--appdir` directory.

Now that you have AutoGen Studio installed and running, you are ready to explore its capabilities, including defining and modifying agent workflows, interacting with agents and sessions, and expanding agent skills.
