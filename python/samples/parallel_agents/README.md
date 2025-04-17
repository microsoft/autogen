# Parallel-Agents

Parallel-Agents is a framework that concurrently runs multiple multi-agent systems in parallel to solve a problem. This example demonstrates how to use the framework to run multiple instances of [Magentic-One](https://github.com/microsoft/autogen/tree/main/python/packages/autogen-magentic-one).

## Setup
1. Create a virtual environment and activate it. AutoGen requires **Python 3.10 or later**.
```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install the required packages.
```bash
pip install -r requirements.txt
```

3. Parallel-Agents uses playwright to interact with web pages. You need to install the playwright dependencies. Run the following command to install the playwright dependencies:
```bash
playwright install --with-deps chromium
```

4. Run the example.
```bash
# This will run the parallel agents with three teams in parallel. The program will wait for all three teams to finish before aggregating a final answer and exiting.
python run_parallel_agents.py --num_teams 3 --num_answers 3
```

5. The output will be saved in several files. `console_log_x.txt` will contain the console output of each team, and `aggregator_log.txt` will contain the aggregated output from all teams.