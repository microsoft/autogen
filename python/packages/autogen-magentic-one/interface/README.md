# Helpers for magentic-one

These scripts provide a simple interface to the magentic-one API.

Additional dependencies:
```bash
pip install flask markdown
```


- magentic-one.py: A simple interface to the magentic-one API.

Problems: uses local code execution, need to move to docker.

- log_viewer.py: A simple flask app to view the logs of the magentic-one API, you need to point it to the .jsonl file

```bash
python log_viewer.py path/to/your/logs.jsonl
```
- test.py: A simple test script to test the magentic-one API.

```bash
python test.py
```
