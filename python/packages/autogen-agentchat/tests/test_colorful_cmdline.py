import re
import pytest
from autogen_agentchat.ui._console import aprint, color_map, get_random_ansi_color, sources


@pytest.mark.asyncio
async def test_aprint_no_color(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that aprint works without color."""
    await aprint("Test message", is_colorful=False, source="Planner")
    captured = capsys.readouterr()
    assert captured.out.strip() == "Test message"


@pytest.mark.asyncio
async def test_aprint_with_color(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that aprint applies color when is_colorful=True."""
    # Clear existing sources for this test
    global sources, color_map
    sources = []
    color_map = {}

    await aprint("Colored message by Planner", is_colorful=True, source="Planner")
    captured = capsys.readouterr()

    # Check that the output contains ANSI color codes and the message
    ansi_pattern = r"\033\[\d+(?:;\d+)*m"
    assert re.search(ansi_pattern, captured.out) is not None
    assert "Colored message" in captured.out
    assert "\033[0m" in captured.out  # Reset code at the end


@pytest.mark.asyncio
async def test_source_tracking() -> None:
    """Test that new sources are added to sources list."""
    # Clear existing sources for this test
    global sources, color_map

    await aprint("Message 1", is_colorful=True, source="SearchTool")
    assert "searchtool" in sources
    assert len(sources) == 1
    assert "searchtool" in color_map

    await aprint("Message 2", is_colorful=True, source="Coder")
    assert "coder" in sources
    assert len(sources) == 2
    assert "coder" in color_map


@pytest.mark.asyncio
async def test_consistent_colors(capsys: pytest.CaptureFixture[str]) -> None:
    """Test that the same source gets the same color in multiple calls."""
    # Clear existing sources for this test
    global sources, color_map

    await aprint("First message", is_colorful=True, source="Assistant")
    first_color = color_map["assistant"]

    await aprint("Second message", is_colorful=True, source="Assistant")
    second_color = color_map["assistant"]

    assert first_color == second_color

    # Also verify the color was actually applied in output
    captured = capsys.readouterr()
    assert first_color in captured.out


@pytest.mark.asyncio
async def test_different_sources_different_colors() -> None:
    """Test that different sources get different colors."""
    # Clear existing sources for this test
    global sources, color_map

    await aprint("Message A", is_colorful=True, source="UserProxy")
    await aprint("Message B", is_colorful=True, source="LLM")

    color_a = color_map["userproxy"]  # Note: source names are lowercased
    color_b = color_map["llm"]

    assert color_a != color_b


@pytest.mark.asyncio
async def test_object_source_name() -> None:
    """Test that object sources are correctly handled."""
    # Clear existing sources for this test
    global sources, color_map

    class SearchAgent:
        pass

    source_obj = SearchAgent()
    await aprint("Object source message", is_colorful=True, source=source_obj)

    assert "searchagent" in sources  # Class name lowercased
    assert "searchagent" in color_map


@pytest.mark.asyncio
async def test_random_color_generation() -> None:
    """Test that random colors are correctly formatted."""
    for _ in range(10):  # Test multiple times to ensure consistency
        color = get_random_ansi_color()
        # Verify the color format matches ANSI RGB format
        assert re.match(r"\033\[38;2;\d{1,3};\d{1,3};\d{1,3}m", color)

        # Extract the RGB values and check their range
        rgb_match = re.search(r"38;2;(\d{1,3});(\d{1,3});(\d{1,3})", color)
        assert rgb_match is not None

        r, g, b = map(int, rgb_match.groups())
        assert 0 <= r <= 255
        assert 0 <= g <= 255
        assert 0 <= b <= 255


@pytest.mark.asyncio
async def test_case_insensitivity() -> None:
    """Test that source names are case-insensitive."""
    global sources, color_map

    await aprint("First message", is_colorful=True, source="PLANNER")
    await aprint("Second message", is_colorful=True, source="planner")
    await aprint("Third message", is_colorful=True, source="Planner")

    # Should only be one source entry regardless of case
    assert len(sources) == 1
    assert len(color_map) == 1
    assert "planner" in sources