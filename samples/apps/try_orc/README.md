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
