from typing import Dict, List, Union
from autogen import agentchat
import pytest

TAG_PARSING_TESTS = [
    {
        "message": "Hello agent, can you take a look at this image <img http://example.com/image.png>",
        "expected": [{"tag": "img", "attr": {"src": "http://example.com/image.png"}}],
    },
    {
        "message": "Can you transcribe this audio? <audio http://example.com/au=dio.mp3>",
        "expected": [{"tag": "audio", "attr": {"src": "http://example.com/au=dio.mp3"}}],
    },
    {
        "message": "Can you describe what's in this image <img url='http://example.com/=image.png'>",
        "expected": [{"tag": "img", "attr": {"url": "http://example.com/=image.png"}}],
    },
    {
        "message": "Can you describe what's in this image <img http://example.com/image.png> and transcribe this audio? <audio http://example.com/audio.mp3>",
        "expected": [
            {"tag": "img", "attr": {"src": "http://example.com/image.png"}},
            {"tag": "audio", "attr": {"src": "http://example.com/audio.mp3"}},
        ],
    },
    {
        "message": "Can you generate this audio? <audio text='Hello I'm a robot' prompt='whisper'>",
        "expected": [{"tag": "audio", "attr": {"text": "Hello I'm a robot", "prompt": "whisper"}}],
    },
    {
        "message": "Can you describe what's in this image <img http://example.com/image.png width='100'> and this image <img http://hello.com/image=.png>?",
        "expected": [
            {"tag": "img", "attr": {"src": "http://example.com/image.png", "width": "100"}},
            {"tag": "img", "attr": {"src": "http://hello.com/image=.png"}},
        ],
    },
    {
        "message": "Text with no tags",
        "expected": [],
    },
]


def _delete_unused_keys(d: Dict) -> None:
    if "match" in d:
        del d["match"]


@pytest.mark.parametrize("test_case", TAG_PARSING_TESTS)
def test_tag_parsing(test_case: Dict[str, Union[str, List[Dict[str, Union[str, Dict[str, str]]]]]]) -> None:
    """Test the tag_parsing function."""
    message = test_case["message"]
    expected = test_case["expected"]
    tags = ["img", "audio", "random"]

    result = []
    for tag in tags:
        parsed_tags = agentchat.utils.parse_tags_from_content(tag, message)
        for item in parsed_tags:
            _delete_unused_keys(item)

        result.extend(parsed_tags)
    assert result == expected

    result = []
    for tag in tags:
        content = [{"type": "text", "text": message}]
        parsed_tags = agentchat.utils.parse_tags_from_content(tag, content)
        for item in parsed_tags:
            _delete_unused_keys(item)

        result.extend(parsed_tags)
    assert result == expected


if __name__ == "__main__":
    test_tag_parsing(TAG_PARSING_TESTS[0])
