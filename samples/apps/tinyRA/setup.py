# setup.py
from setuptools import setup

with open("requirements.txt") as f:
    requirements = f.read().splitlines()

setup(
    name="tinyra",
    version="0.1",
    description="A minimalistic research assistant built with AutoGen.",
    py_modules=["tui"],
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "tinyra = tui:run_tinyra",
        ],
    },
)
