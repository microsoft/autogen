import importlib

from autogenstudio.validation.validation_service import ValidationService


def test_validate_provider_surfaces_original_import_error(monkeypatch):
    """Validation errors should include the original import exception details."""

    def _raise_import_error(_module_path: str):
        raise ImportError("No module named 'vertexai'")

    monkeypatch.setattr(importlib, "import_module", _raise_import_error)

    result = ValidationService.validate_provider("OpenAIChatCompletionClient")

    assert result is not None
    assert result.field == "provider"
    assert "Could not import provider autogen_ext.models.openai.OpenAIChatCompletionClient" in result.error
    assert "No module named 'vertexai'" in result.error
