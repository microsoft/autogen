# Decision Making-ALFWorld
This is the code for evaluating ALFChat on ALFWorld.

## Setup
Download `alfworld` data and install environments following instructions [here](https://github.com/alfworld/alfworld).

Current implementation uses 2.0.1 version of FLAML.

```bash
pip install flaml==2.0.1
```

## Evaluation on Benchmark

Fill in your api-key in `twoagent.py`, then run the following command to evaluate ALFChat (2 agent) on AlfWorld. The conversation history will be saved in `logs_twoagent/`

```bash
python twoagent.py
```
Fill in your api-key in `multiagent.py`, then run the following command to evaluate ALFChat (3 agent) on AlfWorld. The conversation history will be saved in `logs_multiagent/`

```bash
python multiagent.py
```