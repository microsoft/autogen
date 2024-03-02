import os

import setuptools

here = os.path.abspath(os.path.dirname(__file__))

with open("README.md", "r", encoding="UTF-8") as fh:
    long_description = fh.read()

# Get the code version
version = {}
with open(os.path.join(here, "autogen/version.py")) as fp:
    exec(fp.read(), version)
__version__ = version["__version__"]

install_requires = [
    "openai>=1.3",
    "diskcache",
    "termcolor",
    "flaml",
    "python-dotenv",
    "tiktoken",
    # Disallowing 2.6.0 can be removed when this is fixed https://github.com/pydantic/pydantic/issues/8705
    "pydantic>=1.10,<3,!=2.6.0",  # could be both V1 and V2
    "docker",
]

setuptools.setup(
    name="pyautogen",
    version=__version__,
    author="AutoGen",
    author_email="auto-gen@outlook.com",
    description="Enabling Next-Gen LLM Applications via Multi-Agent Conversation Framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/microsoft/autogen",
    packages=setuptools.find_packages(include=["autogen*"], exclude=["test"]),
    install_requires=install_requires,
    extras_require={
        "test": [
            "coverage>=5.3",
            "ipykernel",
            "nbconvert",
            "nbformat",
            "pre-commit",
            "pytest-asyncio",
            "pytest>=6.1.1,<8",
        ],
        "blendsearch": ["flaml[blendsearch]"],
        "mathchat": ["sympy", "pydantic==1.10.9", "wolframalpha"],
        "retrievechat": ["chromadb", "sentence_transformers", "pypdf", "ipython"],
        "autobuild": ["chromadb", "sentence-transformers", "huggingface-hub"],
        "teachable": ["chromadb"],
        "lmm": ["replicate", "pillow"],
        "graph": ["networkx", "matplotlib"],
        "websurfer": ["beautifulsoup4", "markdownify", "pdfminer.six", "pathvalidate"],
        "redis": ["redis"],
        "jupyter-executor": [
            "jupyter-kernel-gateway",
            "websocket-client",
            "requests",
            "jupyter-client>=8.6.0",
            "ipykernel>=6.29.0",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8,<3.13",
)
