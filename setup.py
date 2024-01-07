import os
import setuptools

# Base directory
here = os.path.abspath(os.path.dirname(__file__))

# Read the long description from README
with open("README.md", "r", encoding="UTF-8") as fh:
    long_description = fh.read()

# Get the code version
version = {}
with open(os.path.join(here, "autogen/version.py")) as fp:
    exec(fp.read(), version)
__version__ = version["__version__"]

# Dependencies
install_requires = [
    "diskcache",
    "flaml",
    "openai~=1.3",
    "python-dotenv",
    "termcolor",
    "tiktoken",
    "pydantic>=1.10,<3",
]

# Extras requirements
extras_require = {
    "test": [
        "coverage>=5.3",
        "ipykernel",
        "nbconvert",
        "nbformat",
        "pre-commit",
        "pytest-asyncio",
        "pytest>=6.1.1",
    ],
    "blendsearch": ["flaml[blendsearch]"],
    "mathchat": ["pydantic==1.10.9", "sympy", "wolframalpha"],
    "retrievechat": ["chromadb", "sentence_transformers", "pypdf", "ipython"],
    "teachable": ["chromadb"],
    "lmm": ["pillow", "replicate"],
    "graphs": ["matplotlib~=3.8.1", "networkx~=3.2.1"],
}

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
    extras_require=extras_require,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9, <3.13",
)
