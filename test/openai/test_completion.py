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
        return
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
        result = oai.Completion.eval(analysis.best_config, prune=False, eval_only=True)
        print(result)
    except ImportError as exc:
        print(exc)


if __name__ == "__main__":
    import openai

    openai.api_key_path = "test/openai/key.txt"
    test_humaneval(-1)
