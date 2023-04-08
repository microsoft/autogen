import signal
import subprocess
import sys
from typing import List, Dict, Tuple, Optional, Union, Callable
from flaml import oai


def timeout_handler(signum, frame):
    raise TimeoutError("Timed out!")


def execute_code(code: str, max_exec_time: Optional[int] = 3):
    signal.signal(signal.SIGALRM, timeout_handler)
    code = code.strip()
    with open("codetest.py", "w") as fout:
        fout.write(code)
    try:
        signal.alarm(max_exec_time)
        result = subprocess.run(
            [sys.executable, "codetest.py"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        signal.alarm(0)
    except TimeoutError:
        return 0
    return int(result.returncode == 0)


def generate_assertions(
    definition: str, model: Optional[str] = "gpt-3.5-turbo"
) -> Tuple[str, float]:
    """Generate assertions for a function.

    Args:
        definition (str): The function definition, including the signature and docstr.
        model (str): The model used for generation.

    Returns:
        str: The generated assertions.
        float: The cost of the generation.
    """
    prompt = """Given the signature and docstring, write the exactly same number of assertion(s) for the provided example(s) in the docstring, without assertion messages.

func signature:
{definition}
assertions:"""
    response = oai.Completion.create(
        {"definition": definition},
        model=model,
        prompt=prompt,
        max_tokens=256,
        stop="\n\n",
    )
    cost = oai.Completion.cost(model, response)
    assertions = oai.Completion.extract_text(response)[0]
    return assertions, cost


def _remove_check(response):
    """Remove the check function from the response."""
    # find the position of the check function
    pos = response.find("def check(")
    if pos == -1:
        return response
    return response[:pos]


def eval_function_completions(
    responses: List[str],
    definition: str,
    test: Optional[str] = None,
    entry_point: Optional[str] = None,
    assertions: Optional[Union[str, Callable[[str], Tuple[str, float]]]] = None,
) -> Dict:
    """Select a response from a list of responses for the function completion task (using generated assertions), and/or evaluate if the task is successful using a gold test.

    Args:
        responses (list): The list of responses.
        definition (str): The input definition.
        test (Optional, str): The test code.
        entry_point (Optional, str): The name of the function.
        assertions (Optional, str or Callable): The assertion code which serves as a filter of the responses, or an assertion generator.
            When provided, only the responses that pass the assertions will be considered for the actual test (if provided).

    Returns:
        dict: The success metrics.
    """
    n = len(responses)
    if assertions is None:
        # no assertion filter
        success_list = []
        for i in range(n):
            response = _remove_check(responses[i])
            code = (
                f"{response}\n{test}\ncheck({entry_point})"
                if response.startswith("def")
                else f"{definition}{response}\n{test}\ncheck({entry_point})"
            )
            success = execute_code(code)
            success_list.append(success)
        return {
            "expected_success": 1 - pow(1 - sum(success_list) / n, n),
            "success": any(s for s in success_list),
        }
    if callable(assertions) and n > 1:
        # assertion generator
        assertions, gen_cost = assertions(definition)
    else:
        gen_cost = 0
    if n > 1 or test is None:
        for i in range(n):
            response = responses[i] = _remove_check(responses[i])
            code = (
                f"{response}\n{assertions}"
                if response.startswith("def")
                else f"{definition}{response}\n{assertions}"
            )
            succeed_assertions = execute_code(code)
            if succeed_assertions:
                break
    else:
        # just test, no need to check assertions
        succeed_assertions = False
        i, response = 0, responses[0]
    if test is None:
        # no test code
        return {
            "index_selected": i,
            "succeed_assertions": succeed_assertions,
            "gen_cost": gen_cost,
            "assertions": assertions,
        }
    code_test = (
        f"{response}\n{test}\ncheck({entry_point})"
        if response.startswith("def")
        else f"{definition}{response}\n{test}\ncheck({entry_point})"
    )
    success = execute_code(code_test)
    return {
        "index_selected": i,
        "succeed_assertions": succeed_assertions,
        "success": success,
        "gen_cost": gen_cost,
        "assertions": assertions,
    }


def implement(
    definition: str,
    configs: List[Dict],
    assertions: Optional[
        Union[str, Callable[[str], Tuple[str, float]]]
    ] = generate_assertions,
) -> Tuple[str, float]:
    """Implement a function from a definition.

    Args:
        definition (str): The function definition, including the signature and docstr.
        configs (list): The list of configurations for completion.
        assertions (Optional, str or Callable): The assertion code which serves as a filter of the responses, or an assertion generator.

    Returns:
        str: The implementation.
        float: The cost of the implementation.
        int: The index of the configuration which generates the implementation.
    """
    cost = 0
    if len(configs) > 1 and callable(assertions):
        assertions, cost = assertions(definition)
    for i, config in enumerate(configs):
        response = oai.Completion.create({"definition": definition}, **config)
        cost += oai.Completion.cost(config["model"], response)
        responses = oai.Completion.extract_text(response)
        metrics = eval_function_completions(
            responses, definition, assertions=assertions
        )
        assertions = metrics["assertions"]
        cost += metrics["gen_cost"]
        if metrics["succeed_assertions"] or i == len(configs) - 1:
            return responses[metrics["index_selected"]], cost, i
