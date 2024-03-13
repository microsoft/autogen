from unittest.mock import MagicMock, patch

import pytest

from autogen.agentchat.conversable_agent import ConversableAgent

try:
    from autogen.agentchat.contrib.capabilities.vision_capability import VisionCapability
    from autogen.agentchat.contrib.multimodal_conversable_agent import MultimodalConversableAgent
except ImportError:
    skip_test = True
else:
    skip_test = False


@pytest.fixture
def lmm_config():
    return {
        "config_list": [{"model": "gpt-4-vision-preview", "api_key": "sk-my_key"}],
        "temperature": 0.5,
        "max_tokens": 300,
    }


@pytest.fixture
def vision_capability(lmm_config):
    return VisionCapability(lmm_config)


@pytest.fixture
def conversable_agent():
    return ConversableAgent(name="conversable agent", llm_config=False)


@pytest.fixture
def multimodal_agent():
    return MultimodalConversableAgent(name="sample mm agent", llm_config=False)


@pytest.mark.skipif(
    skip_test,
    reason="do not run if dependency is not installed or requested to skip",
)
def test_add_to_conversable_agent(vision_capability, conversable_agent):
    vision_capability.add_to_agent(conversable_agent)
    assert hasattr(conversable_agent, "process_last_received_message")


@pytest.mark.skipif(
    skip_test,
    reason="do not run if dependency is not installed or requested to skip",
)
def test_add_to_multimodal_agent(vision_capability, multimodal_agent, capsys):
    vision_capability.add_to_agent(multimodal_agent)
    captured = capsys.readouterr()
    assert "already a multimodal agent" in captured.out


@patch("autogen.oai.client.OpenAIWrapper")
@pytest.mark.skipif(
    skip_test,
    reason="do not run if dependency is not installed or requested to skip",
)
def test_process_last_received_message_text(mock_lmm_client, vision_capability):
    mock_lmm_client.create.return_value = MagicMock(choices=[MagicMock(message=MagicMock(content="A description"))])
    content = "Test message without image"
    processed_content = vision_capability.process_last_received_message(content)
    assert processed_content == content


@patch("autogen.agentchat.contrib.img_utils.get_image_data", return_value="base64_image_data")
@patch(
    "autogen.agentchat.contrib.img_utils.convert_base64_to_data_uri",
    return_value="data:image/png;base64,base64_image_data",
)
@patch(
    "autogen.agentchat.contrib.capabilities.vision_capability.VisionCapability._get_image_caption",
    return_value="A sample image caption.",
)
@pytest.mark.skipif(
    skip_test,
    reason="do not run if dependency is not installed or requested to skip",
)
def test_process_last_received_message_with_image(
    mock_get_caption, mock_convert_base64, mock_get_image_data, vision_capability
):
    content = [{"type": "image_url", "image_url": {"url": "notebook/viz_gc.png"}}]
    expected_caption = (
        "<img notebook/viz_gc.png> in case you can not see, the caption of this image is: A sample image caption.\n"
    )
    processed_content = vision_capability.process_last_received_message(content)
    assert processed_content == expected_caption
