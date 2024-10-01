import os
import platform

import setuptools

here = os.path.abspath(os.path.dirname(__file__))

with open("README.md", "r", encoding="UTF-8") as fh:
    long_description = fh.read()

# Get the code version
version = {}
with open(os.path.join(here, "autogen/version.py")) as fp:
    exec(fp.read(), version)
__version__ = version["__version__"]


current_os = platform.system()

install_requires = [
    "openai>=1.3",
    "diskcache",
    "termcolor",
    "flaml",
    # numpy is installed by flaml, but we want to pin the version to below 2.x (see https://github.com/microsoft/autogen/issues/1960)
    "numpy>=1.17.0,<2",
    "python-dotenv",
    "tiktoken",
    # Disallowing 2.6.0 can be removed when this is fixed https://github.com/pydantic/pydantic/issues/8705
    "pydantic>=1.10,<3,!=2.6.0",  # could be both V1 and V2
    "docker",
    "packaging",
]

jupyter_executor = [
    "jupyter-kernel-gateway",
    "websocket-client",
    "requests",
    "jupyter-client>=8.6.0",
    "ipykernel>=6.29.0",
]

retrieve_chat = [
    "protobuf==4.25.3",
    "chromadb",
    "sentence_transformers",
    "pypdf",
    "ipython",
    "beautifulsoup4",
    "markdownify",
]

retrieve_chat_pgvector = [*retrieve_chat, "pgvector>=0.2.5"]

if current_os in ["Windows", "Darwin"]:
    retrieve_chat_pgvector.extend(["psycopg[binary]>=3.1.18"])
elif current_os == "Linux":
    retrieve_chat_pgvector.extend(["psycopg>=3.1.18"])

extra_require = {
    "test": [
        "ipykernel",
        "nbconvert",
        "nbformat",
        "pre-commit",
        "pytest-cov>=5",
        "pytest-asyncio",
        "pytest>=6.1.1,<8",
        "pandas",
    ],
    "blendsearch": ["flaml[blendsearch]"],
    "mathchat": ["sympy", "pydantic==1.10.9", "wolframalpha"],
    "retrievechat": retrieve_chat,
    "retrievechat-pgvector": retrieve_chat_pgvector,
    "retrievechat-mongodb": [*retrieve_chat, "pymongo>=4.0.0"],
    "retrievechat-qdrant": [*retrieve_chat, "qdrant_client", "fastembed>=0.3.1"],
    "retrievechat-couchbase": [*retrieve_chat, "couchbase>=4.3.0"],
    "autobuild": ["chromadb", "sentence-transformers", "huggingface-hub", "pysqlite3"],
    "teachable": ["chromadb"],
    "lmm": ["replicate", "pillow"],
    "graph": ["networkx", "matplotlib"],
    "gemini": ["google-generativeai>=0.5,<1", "google-cloud-aiplatform", "google-auth", "pillow", "pydantic"],
    "together": ["together>=1.2"],
    "websurfer": [
        "beautifulsoup4",
        "markdownify",
        "pathvalidate",
        # for mdconvert
        "puremagic",  # File identification
        "pdfminer.six",  # Pdf
        "mammoth",  # Docx
        "python-pptx",  # Ppts
        "pandas",  # Xlsx
        "openpyxl",
        "youtube_transcript_api==0.6.0",  # Transcription
    ],
    "redis": ["redis"],
    "cosmosdb": ["azure-cosmos>=4.2.0"],
    "websockets": ["websockets>=12.0,<13"],
    "jupyter-executor": jupyter_executor,
    "types": ["mypy==1.9.0", "pytest>=6.1.1,<8"] + jupyter_executor,
    "long-context": ["llmlingua<0.3"],
    "anthropic": ["anthropic>=0.23.1"],
    "cerebras": ["cerebras_cloud_sdk>=1.0.0"],
    "mistral": ["mistralai>=1.0.1"],
    "groq": ["groq>=0.9.0"],
    "cohere": ["cohere>=5.5.8"],
    "ollama": ["ollama>=0.3.1", "fix_busted_json>=0.0.18"],
    "bedrock": ["boto3>=1.34.149"],
}

setuptools.setup(
    name="pyautogen",
    version=__version__,
    author="AutoGen",
    author_email="autogen-contact@service.microsoft.com",
    description="Enabling Next-Gen LLM Applications via Multi-Agent Conversation Framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/microsoft/autogen",
    packages=setuptools.find_packages(include=["autogen*"], exclude=["test"]),
    install_requires=install_requires,
    extras_require=extra_require,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8,<3.13",
)
