import base64
import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from autogenstudio.gallery.builder import create_default_gallery
from autogenstudio.gallery.tools.generate_image import generate_image


def test_default_gallery_uses_available_models() -> None:
    gallery = create_default_gallery()
    models = gallery.components.models
    anthropic = next(model for model in models if model.provider.endswith("AnthropicChatCompletionClient"))
    assert anthropic.config["model"] == "claude-sonnet-4-6"

    bundled_gallery = Path(__file__).parents[1] / "frontend/src/components/views/gallery/default_gallery.json"
    data = json.loads(bundled_gallery.read_text(encoding="utf-8"))
    assert any(model["config"].get("model") == "claude-sonnet-4-6" for model in data["components"]["models"])
    tool = next(tool for tool in data["components"]["tools"] if tool["config"]["name"] == "generate_image")
    assert "gpt-image-2" in tool["config"]["source_code"]
    assert "dall-e-3" not in tool["config"]["source_code"]


@pytest.mark.asyncio
async def test_generate_image_uses_supported_parameters(tmp_path: Path) -> None:
    image = Image.new("RGB", (1, 1))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    mock_client = MagicMock()
    mock_client.images.generate.return_value.data = [MagicMock(b64_json=base64.b64encode(buffer.getvalue()).decode())]

    with patch("autogenstudio.gallery.tools.generate_image.OpenAI", return_value=mock_client):
        files = await generate_image("A red circle", output_dir=tmp_path, image_size="1024x1024")

    mock_client.images.generate.assert_called_once_with(
        model="gpt-image-2", prompt="A red circle", n=1, size="1024x1024"
    )
    assert len(files) == 1
    assert Path(files[0]).is_file()
