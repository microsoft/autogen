import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
from nbconvert.preprocessors import CellExecutionError
import os
import sys
import pytest


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
    sys.platform != "darwin" or "3.8" not in sys.version,
    reason="Only run on macOS with Python 3.8",
)
def test_automl_classification(save=False):
    run_notebook("automl_classification.ipynb", save=save)


@pytest.mark.skipif(
    sys.platform != "darwin" or "3.7" not in sys.version,
    reason="Only run on macOS with Python 3.7",
)
def test_zeroshot_lightgbm(save=False):
    run_notebook("zeroshot_lightgbm.ipynb", save=save)


if __name__ == "__main__":
    # test_automl_classification(save=True)
    test_zeroshot_lightgbm(save=True)
