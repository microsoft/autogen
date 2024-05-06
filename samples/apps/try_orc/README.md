# GAIA Orchestrator Agent Demo

This directory contains a sample application designed to demonstrate the capabilities of the orchestrator developed for the GAIA benchmark.

## Getting Started

### Prerequisites

The application should be run in a virtual environment to ensure that its dependencies do not interfere with any existing Python packages you may have. You can use any virtual environment manager you prefer, such as venv or conda.

### Installation

1. Clone this repository to your local machine.
2. Navigate to the `try_orc` directory within the cloned repository:

    ```bash
    cd try_orc
    ```

3. Install the required Python packages:

    ```bash
    pip install -r requirements.txt
    ```

### Running the Application

First you need to set up your LLM keys and configuration. You can do this by
creating a file called `OAI_CONFIG_LIST` or export an environment variable
with the same name and content. Its basically a JSON string that defines
various properties like model names, api keys, base urls, etc.

Please see the contents of `OAI_CONFIG_LIST_sample` in this directory for an example.
Modify it with your keys and configuration and rename it to `OAI_CONFIG_LIST`.

*Note*: The config list must contain one multi-modal model tagged with "mlm" and one (at least) text model tagged with "llm"


Once you've installed the required packages, you can run the application with the following command:

```bash
python <demo file>
```

There are several demos available:

| Demo File | Orchestrator | Agents |
| -------- | -------- | -------- |
| `demo_orc_twoagents.py`   | text   | coder, computer terminal   |
| `demo_orc_mdwebsurfer.py`   | text   | \+ web surfer (md)  |
| `demo_orc_mmwebsurfer.py`   | mm   | web surfer (md) &rarr; web surfer (mm) |


*Note*: Multi-modal webbrowser requires playwright. You can install it using the following instructions:

```
pip install playwright
playwright install --with-deps chromium
```
