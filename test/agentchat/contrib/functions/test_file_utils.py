import sys
import os
import pytest
from autogen.agentchat.contrib.functions import file_utils as fu

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from conftest import skip_openai  # noqa: E402

try:
    from openai import OpenAI
except ImportError:
    skip = True
else:
    skip = False or skip_openai

TESTDIR = os.path.join(os.path.join(os.path.dirname(__file__), "..", "..", ".."), "test_files")


def test_read_text_from_pdf():
    text = fu.read_text_from_pdf(os.path.join(TESTDIR, "example.pdf"))
    assert isinstance(text, str)


def test_read_text_from_docx():
    text = fu.read_text_from_docx(os.path.join(TESTDIR, "example.docx"))
    assert isinstance(text, str)


def test_read_text_from_image():
    for file in ["example.jpg", "example.png"]:
        text = fu.read_text_from_image(os.path.join(TESTDIR, file))
        assert isinstance(text, str)


def test_read_text_from_pptx():
    text = fu.read_text_from_pptx(os.path.join(TESTDIR, "example.pptx"))
    assert isinstance(text, str)


def test_read_text_from_xlsx():
    text = fu.read_text_from_xlsx(os.path.join(TESTDIR, "example.xlsx"))
    assert isinstance(text, str)


# def test_read_text_from_audio():
# TODO: Needs work + smaller test file
#     for file in ["example.wav"]:
#         text = fu.read_text_from_audio(os.path.join(TESTDIR, file))
#         print(text)
#     assert isinstance(text, str)


@pytest.mark.skipif(
    sys.platform in ["darwin", "win32"] or skip,
    reason="do not run on MacOS or windows OR openai not installed OR requested to skip",
)
def test_caption_image_using_gpt4v():
    for file in ["example.jpg", "example.png"]:
        text = fu.caption_image_using_gpt4v(os.path.join(TESTDIR, file))
        assert isinstance(text, str)
