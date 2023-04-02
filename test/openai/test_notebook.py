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


def run_notebook(input_nb, output_nb="executed_openai_notebook.ipynb", save=False):
    try:
        file_path = os.path.join(here, os.pardir, os.pardir, "notebook", input_nb)
        with open(file_path) as f:
            nb = nbformat.read(f, as_version=4)
        ep = ExecutePreprocessor(timeout=3600, kernel_name="python3")
        ep.preprocess(nb, {"metadata": {"path": here}})

        output_file_name = "executed_openai_notebook_output.txt"
        output_file = os.path.join(here, output_file_name)
        with open(output_file, "a") as f:
            for cell in nb.cells:
                if cell.cell_type == "code" and "outputs" in cell:
                    for output in cell.outputs:
                        if "text" in output:
                            f.write(output["text"].strip() + "\n")
                        elif "data" in output and "text/plain" in output["data"]:
                            f.write(output["data"]["text/plain"].strip() + "\n")
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
    run_notebook("integrate_chatgpt.ipynb", save=save)


if __name__ == "__main__":
    test_integrate_chatgpt(save=True)
    test_integrate_openai(save=True)
