#!/usr/bin/env python

# Equivalent to running the basj script below, but with an additional check if the files was moved:
# cd ../../..
# pip install -e .[websockets] fastapi uvicorn

import subprocess
from pathlib import Path

repo_root = Path(__file__).parents[3]
if not (repo_root / "setup.py").exists():
    raise RuntimeError("This script has been moved, please run it from its original location.")

print("Installing the package in editable mode, with the websockets extra, and fastapi and uvicorn...", flush=True)
subprocess.run(["pip", "install", "-e", ".[websockets]", "fastapi", "uvicorn"], cwd=repo_root, check=True)
