import datasets
import signal
import subprocess
import sys
import numpy as np
import pytest
from flaml import oai


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="do not run on windows",
)
def test_humaneval(num_samples=1):
    def timeout_handler(signum, frame):
        raise TimeoutError("Timed out!")

    signal.signal(signal.SIGALRM, timeout_handler)
    max_exec_time = 3  # seconds

    def execute_code(code):
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

    def success_metrics(responses, prompt, test, entry_point):
        """Check if the response is correct.

        Args:
            responses (list): The list of responses.
            prompt (str): The input prompt.
            test (str): The test code.
            entry_point (str): The name of the function.

        Returns:
            dict: The success metrics.
        """
        success_list = []
        n = len(responses)
        for i in range(n):
            response = responses[i]
            code = f"{prompt}{response}\n{test}\ncheck({entry_point})"
            succeed = execute_code(code)
            success_list.append(succeed)
        return {
            "expected_success": 1 - pow(1 - np.mean(success_list), n),
            "success": any(s for s in success_list),
        }

    seed = 41
    data = datasets.load_dataset("openai_humaneval")["test"].shuffle(seed=seed)
    n_tune_data = 20
    tune_data = [
        {
            "prompt": data[x]["prompt"],
            "test": data[x]["test"],
            "entry_point": data[x]["entry_point"],
        }
        for x in range(n_tune_data)
    ]
    test_data = [
        {
            "prompt": data[x]["prompt"],
            "test": data[x]["test"],
            "entry_point": data[x]["entry_point"],
        }
        for x in range(n_tune_data, len(data))
    ]
    oai.Completion.set_cache(seed)
    try:
        # a minimal tuning example
        config, _ = oai.Completion.tune(
            data=tune_data,
            metric="success",
            mode="max",
            eval_func=success_metrics,
            n=1,
        )
        responses = oai.Completion.create(context=test_data[0], **config)
        # a minimal tuning example for tuning chat completion models using the Completion class
        config, _ = oai.Completion.tune(
            data=tune_data,
            metric="success",
            mode="max",
            eval_func=success_metrics,
            n=1,
            model="gpt-3.5-turbo",
        )
        responses = oai.Completion.create(context=test_data[0], **config)
        # a minimal tuning example for tuning chat completion models using the Completion class
        config, _ = oai.ChatCompletion.tune(
            data=tune_data,
            metric="success",
            mode="max",
            eval_func=success_metrics,
            n=1,
            messages=[{"role": "user", "content": "{prompt}"}],
        )
        responses = oai.ChatCompletion.create(context=test_data[0], **config)
        print(responses)
        # a more comprehensive tuning example
        config, analysis = oai.Completion.tune(
            data=tune_data,
            metric="expected_success",
            mode="max",
            eval_func=success_metrics,
            log_file_name="logs/humaneval.log",
            inference_budget=0.002,
            optimization_budget=2,
            num_samples=num_samples,
            prompt=[
                "{prompt}",
                "# Python 3{prompt}",
                "Complete the following Python function:{prompt}",
                "Complete the following Python function while including necessary import statements inside the function:{prompt}",
            ],
            stop=["\nclass", "\ndef", "\nif", "\nprint"],
        )
        print(config)
        print(analysis.best_result)
        print(test_data[0])
        responses = oai.Completion.create(context=test_data[0], **config)
        print(responses)
        oai.Completion.data = test_data[:num_samples]
        result = oai.Completion._eval(analysis.best_config, prune=False, eval_only=True)
        print("result without pruning", result)
        result = oai.Completion.test(test_data[:num_samples], config=config)
        print(result)
    except ImportError as exc:
        print(exc)


def test_math(num_samples=-1):
    from typing import Optional

    def remove_boxed(string: str) -> Optional[str]:
        """Source: https://github.com/hendrycks/math
        Extract the text within a \\boxed{...} environment.
        Example:
        >>> remove_boxed(\\boxed{\\frac{2}{3}})
        \\frac{2}{3}
        """
        left = "\\boxed{"
        try:
            assert string[: len(left)] == left
            assert string[-1] == "}"
            return string[len(left) : -1]
        except Exception:
            return None

    def last_boxed_only_string(string: str) -> Optional[str]:
        """Source: https://github.com/hendrycks/math
        Extract the last \\boxed{...} or \\fbox{...} element from a string.
        """
        idx = string.rfind("\\boxed")
        if idx < 0:
            idx = string.rfind("\\fbox")
            if idx < 0:
                return None

        i = idx
        right_brace_idx = None
        num_left_braces_open = 0
        while i < len(string):
            if string[i] == "{":
                num_left_braces_open += 1
            if string[i] == "}":
                num_left_braces_open -= 1
                if num_left_braces_open == 0:
                    right_brace_idx = i
                    break
            i += 1

        if right_brace_idx is None:
            retval = None
        else:
            retval = string[idx : right_brace_idx + 1]

        return retval

    def _fix_fracs(string: str) -> str:
        """Source: https://github.com/hendrycks/math
        Reformat fractions.
        Examples:
        >>> _fix_fracs("\\frac1b")
        \frac{1}{b}
        >>> _fix_fracs("\\frac12")
        \frac{1}{2}
        >>> _fix_fracs("\\frac1{72}")
        \frac{1}{72}
        """
        substrs = string.split("\\frac")
        new_str = substrs[0]
        if len(substrs) > 1:
            substrs = substrs[1:]
            for substr in substrs:
                new_str += "\\frac"
                if substr[0] == "{":
                    new_str += substr
                else:
                    try:
                        assert len(substr) >= 2
                    except Exception:
                        return string
                    a = substr[0]
                    b = substr[1]
                    if b != "{":
                        if len(substr) > 2:
                            post_substr = substr[2:]
                            new_str += "{" + a + "}{" + b + "}" + post_substr
                        else:
                            new_str += "{" + a + "}{" + b + "}"
                    else:
                        if len(substr) > 2:
                            post_substr = substr[2:]
                            new_str += "{" + a + "}" + b + post_substr
                        else:
                            new_str += "{" + a + "}" + b
        string = new_str
        return string

    def _fix_a_slash_b(string: str) -> str:
        """Source: https://github.com/hendrycks/math
        Reformat fractions formatted as a/b to \\frac{a}{b}.
        Example:
        >>> _fix_a_slash_b("2/3")
        \frac{2}{3}
        """
        if len(string.split("/")) != 2:
            return string
        a_str = string.split("/")[0]
        b_str = string.split("/")[1]
        try:
            a = int(a_str)
            b = int(b_str)
            assert string == "{}/{}".format(a, b)
            new_string = "\\frac{" + str(a) + "}{" + str(b) + "}"
            return new_string
        except Exception:
            return string

    def _remove_right_units(string: str) -> str:
        """Source: https://github.com/hendrycks/math"""
        if "\\text{ " in string:
            splits = string.split("\\text{ ")
            assert len(splits) == 2
            return splits[0]
        else:
            return string

    def _fix_sqrt(string: str) -> str:
        """Source: https://github.com/hendrycks/math"""
        if "\\sqrt" not in string:
            return string
        splits = string.split("\\sqrt")
        new_string = splits[0]
        for split in splits[1:]:
            if split[0] != "{":
                a = split[0]
                new_substr = "\\sqrt{" + a + "}" + split[1:]
            else:
                new_substr = "\\sqrt" + split
            new_string += new_substr
        return new_string

    def _strip_string(string: str) -> str:
        """Source: https://github.com/hendrycks/math
        Apply the reformatting helper functions above.
        """
        # linebreaks
        string = string.replace("\n", "")
        # print(string)

        # remove inverse spaces
        string = string.replace("\\!", "")
        # print(string)

        # replace \\ with \
        string = string.replace("\\\\", "\\")
        # print(string)

        # replace tfrac and dfrac with frac
        string = string.replace("tfrac", "frac")
        string = string.replace("dfrac", "frac")
        # print(string)

        # remove \left and \right
        string = string.replace("\\left", "")
        string = string.replace("\\right", "")
        # print(string)

        # Remove circ (degrees)
        string = string.replace("^{\\circ}", "")
        string = string.replace("^\\circ", "")

        # remove dollar signs
        string = string.replace("\\$", "")

        # remove units (on the right)
        string = _remove_right_units(string)

        # remove percentage
        string = string.replace("\\%", "")
        string = string.replace(r"\%", "")

        # " 0." equivalent to " ." and "{0." equivalent to "{." Alternatively, add "0" if "." is the start of the string
        string = string.replace(" .", " 0.")
        string = string.replace("{.", "{0.")
        # if empty, return empty string
        if len(string) == 0:
            return string
        if string[0] == ".":
            string = "0" + string

        # to consider: get rid of e.g. "k = " or "q = " at beginning
        if len(string.split("=")) == 2:
            if len(string.split("=")[0]) <= 2:
                string = string.split("=")[1]

        # fix sqrt3 --> sqrt{3}
        string = _fix_sqrt(string)

        # remove spaces
        string = string.replace(" ", "")

        # \frac1b or \frac12 --> \frac{1}{b} and \frac{1}{2}, etc.
        # Even works with \frac1{72} (but not \frac{72}1).
        # Also does a/b --> \\frac{a}{b}
        string = _fix_fracs(string)

        # manually change 0.5 --> \frac{1}{2}
        if string == "0.5":
            string = "\\frac{1}{2}"

        # NOTE: X/Y changed to \frac{X}{Y} in dataset, but in simple cases fix in case the model output is X/Y
        string = _fix_a_slash_b(string)

        return string

    def get_answer(solution: Optional[str]) -> Optional[str]:
        if solution is None:
            return None
        last_boxed = last_boxed_only_string(solution)
        if last_boxed is None:
            return None
        answer = remove_boxed(last_boxed)
        if answer is None:
            return None
        return answer

    def is_equiv(str1: Optional[str], str2: Optional[str]) -> float:
        """Returns (as a float) whether two strings containing math are equivalent up to differences of formatting in
        - units
        - fractions
        - square roots
        - superfluous LaTeX.
        Source: https://github.com/hendrycks/math
        """
        if str1 is None and str2 is None:
            print("WARNING: Both None")
            return 1.0
        if str1 is None or str2 is None:
            return 0.0

        try:
            ss1 = _strip_string(str1)
            ss2 = _strip_string(str2)
            return float(ss1 == ss2)
        except Exception:
            return float(str1 == str2)

    def is_equiv_chain_of_thought(str1: str, str2: str) -> float:
        """Strips the solution first before calling `is_equiv`."""
        ans1 = get_answer(str1)
        ans2 = get_answer(str2)

        return is_equiv(ans1, ans2)

    def success_metrics(responses, solution, **args):
        """Check if each response is correct.

        Args:
            responses (list): The list of responses.
            solution (str): The canonical solution.

        Returns:
            dict: The success metrics.
        """
        success_list = []
        n = len(responses)
        for i in range(n):
            response = responses[i]
            succeed = is_equiv_chain_of_thought(response, solution)
            success_list.append(succeed)
        return {
            "expected_success": 1 - pow(1 - sum(success_list) / n, n),
            "success": any(s for s in success_list),
        }

    seed = 41
    data = datasets.load_dataset("competition_math")
    train_data = data["train"].shuffle(seed=seed)
    test_data = data["test"].shuffle(seed=seed)
    n_tune_data = 20
    tune_data = [
        {
            "problem": train_data[x]["problem"],
            "solution": train_data[x]["solution"],
        }
        for x in range(len(train_data))
        if train_data[x]["level"] == "Level 1"
    ][:n_tune_data]
    test_data = [
        {
            "problem": test_data[x]["problem"],
            "solution": test_data[x]["solution"],
        }
        for x in range(len(test_data))
        if test_data[x]["level"] == "Level 1"
    ]
    print(
        "max tokens in tuning data's canonical solutions",
        max([len(x["solution"].split()) for x in tune_data]),
    )
    print(len(tune_data), len(test_data))
    # prompt template
    prompts = [
        lambda data: "Given a mathematics problem, determine the answer. Simplify your answer as much as possible.\n###\nProblem: What is the value of $\\sqrt{3! \\cdot 3!}$ expressed as a positive integer?\nAnswer: $\\sqrt{3!\\cdot3!}$ is equal to $\\sqrt{(3!)^2}=3!=3\\cdot2\\cdot1=\\boxed{6}$.\n###\nProblem: %s\nAnswer:"
        + data["problem"]
    ]

    try:
        oai.ChatCompletion.set_cache(seed)
        vanilla_config = {
            "model": "gpt-3.5-turbo",
            "temperature": 1,
            "max_tokens": 2048,
            "n": 1,
            "prompt": prompts[0],
            "stop": "###",
        }
        test_data_sample = test_data[0:3]
        result = oai.ChatCompletion.test(
            test_data_sample, vanilla_config, success_metrics
        )
        test_data_sample = test_data[3:6]
        result = oai.ChatCompletion.test(
            test_data_sample,
            vanilla_config,
            success_metrics,
            use_cache=False,
            agg_method="median",
        )

        def my_median(results):
            return np.median(results)

        def my_average(results):
            return np.mean(results)

        result = oai.ChatCompletion.test(
            test_data_sample,
            vanilla_config,
            success_metrics,
            use_cache=False,
            agg_method=my_median,
        )
        result = oai.ChatCompletion.test(
            test_data_sample,
            vanilla_config,
            success_metrics,
            use_cache=False,
            agg_method={"expected_success": my_median, "success": my_average},
        )

        print(result)

        config, _ = oai.ChatCompletion.tune(
            data=tune_data,  # the data for tuning
            metric="expected_success",  # the metric to optimize
            mode="max",  # the optimization mode
            eval_func=success_metrics,  # the evaluation function to return the success metrics
            # log_file_name="logs/math.log",  # the log file name
            inference_budget=0.002,  # the inference budget (dollar)
            optimization_budget=0.01,  # the optimization budget (dollar)
            num_samples=num_samples,
            prompt=prompts,  # the prompt templates to choose from
            stop="###",  # the stop sequence
        )
        print("tuned config", config)
        result = oai.ChatCompletion.test(test_data_sample, config)
        print("result from tuned config:", result)
    except (ImportError, NameError) as exc:
        print(exc)


if __name__ == "__main__":
    import openai

    openai.api_key_path = "test/openai/key.txt"
    test_humaneval(-1)
    test_math(-1)
