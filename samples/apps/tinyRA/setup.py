# setup.py
from setuptools import setup
import subprocess
import os


setup(
    name="tinyra",
    version="0.1",
    description="A minimalistic research assistant built with AutoGen.",
    py_modules=["tui"],
    entry_points={
        "console_scripts": [
            "tinyra = tui:run_tinyra",
        ],
    },
)
