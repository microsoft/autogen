import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
from nbconvert.preprocessors import CellExecutionError
from flaml.tune.spark.utils import check_spark
import os
import pytest

spark_available, _ = check_spark()
skip_spark = not spark_available

pytestmark = pytest.mark.skipif(
    skip_spark, reason="Spark is not installed. Skip all spark tests."
)

here = os.path.abspath(os.path.dirname(__file__))
os.environ["FLAML_MAX_CONCURRENT"] = "2"


def run_notebook(input_nb, output_nb="executed_notebook.ipynb", save=False):
    try:
        file_path = os.path.join(here, os.pardir, os.pardir, "notebook", input_nb)
        with open(file_path) as f:
            nb = nbformat.read(f, as_version=4)
        ep = ExecutePreprocessor(timeout=600, kernel_name="python3")
        ep.preprocess(nb, {"metadata": {"path": here}})
    except CellExecutionError:
        raise
    except Exception as e:
        print("\nIgnoring below error:\n", e, "\n\n")
    finally:
        if save:
            with open(os.path.join(here, output_nb), "w", encoding="utf-8") as f:
                nbformat.write(nb, f)


def test_automl_lightgbm_test():
    run_notebook("integrate_spark.ipynb")


if __name__ == "__main__":
    test_automl_lightgbm_test()
