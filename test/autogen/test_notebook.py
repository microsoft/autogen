import sys
import os
import pytest

try:
    import openai

    skip = False
except ImportError:
    skip = True


here = os.path.abspath(os.path.dirname(__file__))


def run_notebook(input_nb, output_nb="executed_openai_notebook.ipynb", save=False):
    import nbformat
    from nbconvert.preprocessors import ExecutePreprocessor
    from nbconvert.preprocessors import CellExecutionError

    try:
        nb_loc = os.path.join(here, os.pardir, os.pardir, "notebook")
        file_path = os.path.join(nb_loc, input_nb)
        with open(file_path) as nb_file:
            nb = nbformat.read(nb_file, as_version=4)
        preprocessor = ExecutePreprocessor(timeout=4800, kernel_name="python3")
        preprocessor.preprocess(nb, {"metadata": {"path": nb_loc}})

        output_file_name = "executed_openai_notebook_output.txt"
        output_file = os.path.join(here, output_file_name)
        with open(output_file, "a") as nb_output_file:
            for cell in nb.cells:
                if cell.cell_type == "code" and "outputs" in cell:
                    for output in cell.outputs:
                        if "text" in output:
                            nb_output_file.write(output["text"].strip() + "\n")
                        elif "data" in output and "text/plain" in output["data"]:
                            nb_output_file.write(output["data"]["text/plain"].strip() + "\n")
    except CellExecutionError:
        raise
    finally:
        if save:
            with open(os.path.join(here, output_nb), "w", encoding="utf-8") as nb_executed_file:
                nbformat.write(nb, nb_executed_file)


@pytest.mark.skipif(
    skip or not sys.version.startswith("3.10"),
    reason="do not run if openai is not installed or py!=3.10",
)
def test_autogen_agentchat_auto_feedback_from_code(save=False):
    run_notebook("autogen_agentchat_auto_feedback_from_code_execution.ipynb", save=save)


@pytest.mark.skipif(
    skip or not sys.version.startswith("3.10"),
    reason="do not run if openai is not installed or py!=3.10",
)
def test_autogen_openai_completion(save=False):
    run_notebook("autogen_openai_completion.ipynb", save=save)


@pytest.mark.skipif(
    skip or not sys.version.startswith("3.10"),
    reason="do not run if openai is not installed or py!=3.10",
)
def test_autogen_agentchat_function_call(save=False):
    run_notebook("autogen_agentchat_function_call.ipynb", save=save)


@pytest.mark.skipif(
    skip or not sys.version.startswith("3.10"),
    reason="do not run if openai is not installed or py!=3.10",
)
def test_autogen_agentchat_MathChat(save=False):
    run_notebook("autogen_agentchat_MathChat.ipynb", save=save)


@pytest.mark.skipif(
    skip or not sys.version.startswith("3.11"),
    reason="do not run if openai is not installed or py!=3.11",
)
def test_autogen_chatgpt_gpt4(save=False):
    run_notebook("autogen_chatgpt_gpt4.ipynb", save=save)


if __name__ == "__main__":
    test_autogen_agentchat_auto_feedback_from_code(save=True)
    # test_autogen_chatgpt_gpt4(save=True)
    # test_autogen_openai_completion(save=True)
    # test_autogen_agentchat_MathChat(save=True)
    # test_autogen_agentchat_function_call(save=True)
