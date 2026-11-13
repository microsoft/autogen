import asyncio
import base64
import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

from autogenstudio.gallery.tools.generate_image import generate_image


def test_default_gallery_uses_supported_models(tmp_path: Path) -> None:
    gallery_path = Path(__file__).resolve().parents[1] / "frontend/src/components/views/gallery/default_gallery.json"
    gallery = json.loads(gallery_path.read_text())
    models = gallery["components"]["models"]
    assert any(model["config"].get("model") == "claude-sonnet-4-6" for model in models)

    image_tool = next(tool for tool in gallery["components"]["tools"] if tool["config"].get("name") == "generate_image")
    assert 'model="gpt-image-2"' in image_tool["config"]["source_code"]

    image = Image.new("RGB", (1, 1), "red")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    encoded_image = base64.b64encode(buffer.getvalue()).decode()

    with patch("autogenstudio.gallery.tools.generate_image.OpenAI") as openai_client:
        openai_client.return_value.images.generate.return_value = SimpleNamespace(
            data=[SimpleNamespace(b64_json=encoded_image)]
        )
        paths = asyncio.run(generate_image("a red pixel", tmp_path, "1024x1536"))

    openai_client.return_value.images.generate.assert_called_once_with(
        model="gpt-image-2", prompt="a red pixel", n=1, size="1024x1536"
    )
    assert len(paths) == 1
    assert Path(paths[0]).is_file()
