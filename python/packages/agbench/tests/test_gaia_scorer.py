import importlib.util
from pathlib import Path
import sys
import pytest

# Ensure agbench src is on sys.path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Load gaia_question_scorer dynamically from custom_tabulate.py by path
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "benchmarks" / "GAIA" / "Scripts"
CUSTOM_TABULATE_PATH = SCRIPTS_DIR / "custom_tabulate.py"

spec = importlib.util.spec_from_file_location("gaia_custom_tabulate", str(CUSTOM_TABULATE_PATH))
assert spec is not None and spec.loader is not None
gaia_tabulate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gaia_tabulate)
gaia_question_scorer = gaia_tabulate.gaia_question_scorer


@pytest.mark.parametrize(
    "model_answer, ground_truth, expected",
    [
        # Empty / whitespace / punctuation only ground truth should return False
        ("", "", False),
        ("   ", "", False),
        ("...", "", False),
        ("", "   ", False),
        ("", "!!!", False),
        (".", "?!", False),
        ("Paris", "", False),
        ("", "Paris", False),
        ("Rome", "Paris", False),
        # Valid matching answers
        ("Paris.", "paris", True),
        ("sea gull", "seagull", True),
        ("3", "3.0", True),
        ("a, b", "a,b", True),
        ("1, 2, 3", "1,2,3", True),
    ],
)
def test_gaia_question_scorer_empty_and_valid_ground_truth(
    model_answer: str, ground_truth: str, expected: bool
) -> None:
    assert gaia_question_scorer(model_answer, ground_truth) == expected
