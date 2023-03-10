import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
from nbconvert.preprocessors import CellExecutionError
import os
import pytest

try:
    import openai

    skip = False
except ImportError:
    skip = True


here = os.path.abspath(os.path.dirname(__file__))


def run_notebook(input_nb, output_nb="executed_notebook.ipynb", save=False):
    try:
        file_path = os.path.join(here, os.pardir, os.pardir, "notebook", input_nb)
        with open(file_path) as f:
            nb = nbformat.read(f, as_version=4)
        ep = ExecutePreprocessor(timeout=3600, kernel_name="python3")
        ep.preprocess(nb, {"metadata": {"path": here}})
    except CellExecutionError:
        raise
    finally:
        if save:
            with open(os.path.join(here, output_nb), "w", encoding="utf-8") as f:
                nbformat.write(nb, f)


@pytest.mark.skipif(
    skip,
    reason="do not run openai test if openai is not installed",
)
def test_integrate_openai(save=False):
    run_notebook("integrate_openai.ipynb", save=save)


@pytest.mark.skipif(
    skip,
    reason="do not run openai test if openai is not installed",
)
def test_integrate_chatgpt(save=False):
    run_notebook("integrate_chatgpt_math.ipynb", save=save)


if __name__ == "__main__":
    test_integrate_chatgpt(save=True)
