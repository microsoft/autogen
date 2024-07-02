from unittest.mock import MagicMock, patch

import pytest

try:
    from autogen.oai.ollama import OllamaClient

    skip = False
except ImportError:
    OllamaClient = object
    InternalServerError = object
    skip = True

# TODO
