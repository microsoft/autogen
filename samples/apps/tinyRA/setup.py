# setup.py
from setuptools import setup

setup(
    name="tinyra",
    version="0.1",
    description="A minimalistic research assistant built with AutoGen.",
    py_modules=["tinyra"],
    entry_points={
        "console_scripts": [
            "tinyra = tinyra:main",
        ],
    },
)
