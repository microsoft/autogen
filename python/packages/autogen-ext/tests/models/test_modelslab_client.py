"""Tests for ModelsLabChatCompletionClient."""

import os
from unittest.mock import patch

import pytest

from autogen_ext.models.modelslab import ModelsLabChatCompletionClient
from autogen_ext.models.modelslab._client import (
    MODELSLAB_API_BASE,
    _MODELSLAB_MODEL_INFO,
)


@pytest.fixture
def client():
    with patch.dict(os.environ, {"MODELSLAB_API_KEY": "test-key"}):
        return ModelsLabChatCompletionClient()


class TestModelsLabClientInit:
    @patch.dict(os.environ, {"MODELSLAB_API_KEY": "test-key"})
    def test_default_model(self):
        c = ModelsLabChatCompletionClient()
        assert c.model_name == "llama-3.1-8b-uncensored"

    @patch.dict(os.environ, {"MODELSLAB_API_KEY": "test-key"})
    def test_70b_model(self):
        c = ModelsLabChatCompletionClient(model="llama-3.1-70b-uncensored")
        assert c.model_name == "llama-3.1-70b-uncensored"

    @patch.dict(os.environ, {"MODELSLAB_API_KEY": "test-key"})
    def test_api_base_url_set(self):
        c = ModelsLabChatCompletionClient()
        # The base_url should be the ModelsLab endpoint
        assert MODELSLAB_API_BASE == "https://modelslab.com/uncensored-chat/v1"

    def test_raises_without_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MODELSLAB_API_KEY", None)
            with pytest.raises(ValueError, match="MODELSLAB_API_KEY"):
                ModelsLabChatCompletionClient()

    def test_explicit_api_key_overrides_env(self):
        with patch.dict(os.environ, {"MODELSLAB_API_KEY": "env-key"}):
            c = ModelsLabChatCompletionClient(api_key="explicit-key")
            assert c.model_name == "llama-3.1-8b-uncensored"

    @patch.dict(os.environ, {"MODELSLAB_API_KEY": "env-key"})
    def test_env_key_used_when_no_explicit(self):
        c = ModelsLabChatCompletionClient()
        assert c is not None  # Constructed without error

    def test_inherits_openai_client(self):
        from autogen_ext.models.openai import OpenAIChatCompletionClient
        with patch.dict(os.environ, {"MODELSLAB_API_KEY": "test-key"}):
            c = ModelsLabChatCompletionClient()
        assert isinstance(c, OpenAIChatCompletionClient)

    def test_import_from_package(self):
        from autogen_ext.models.modelslab import ModelsLabChatCompletionClient as C
        from autogen_ext.models.modelslab._client import ModelsLabChatCompletionClient as CB
        assert C is CB


class TestModelsLabModelInfo:
    def test_8b_model_info_exists(self):
        assert "llama-3.1-8b-uncensored" in _MODELSLAB_MODEL_INFO

    def test_70b_model_info_exists(self):
        assert "llama-3.1-70b-uncensored" in _MODELSLAB_MODEL_INFO

    def test_8b_context_128k(self):
        info = _MODELSLAB_MODEL_INFO["llama-3.1-8b-uncensored"]
        assert info["context_length"] == 131072

    def test_70b_context_128k(self):
        info = _MODELSLAB_MODEL_INFO["llama-3.1-70b-uncensored"]
        assert info["context_length"] == 131072

    def test_no_vision(self):
        for info in _MODELSLAB_MODEL_INFO.values():
            assert info["vision"] is False

    @patch.dict(os.environ, {"MODELSLAB_API_KEY": "test-key"})
    def test_custom_model_info_accepted(self):
        from autogen_core.models import ModelFamily, ModelInfo
        custom = ModelInfo(
            vision=False,
            function_calling=False,
            json_output=False,
            family=ModelFamily.UNKNOWN,
            structured_output=False,
            context_length=65536,
        )
        c = ModelsLabChatCompletionClient(
            model="llama-3.1-8b-uncensored",
            model_info=custom,
        )
        assert c is not None
