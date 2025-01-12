import sys, os
import yaml
import asyncio
import importlib
from typing import Tuple
from autogen_ext.agentic_memory import PageLog, Grader
from autogen_ext.agentic_memory.eval_framework.clients._client_creator import ClientCreator


def get_task_by_name(task_name):
    path_to_this_file = os.path.abspath(__file__)
    dir_of_this_file = os.path.dirname(path_to_this_file)
    task_filepath = os.path.join(dir_of_this_file, 'tasks', task_name + '.yaml')
    with open(task_filepath, "r") as file:
        task = yaml.load(file, Loader=yaml.FullLoader)
        assert task["name"] == task_name
        return task


async def eval_teachability(fast_learner, evaluator, client, page_log, settings):
    """An evaluation"""
    page = page_log.begin_page(
        summary="eval_teachability",
        details='',
        method_call="eval_teachability")

    task_details = get_task_by_name("autogen_package")
    task_description = task_details["task_description"]
    answer = task_details["expected_answer"]
    grader = Grader(client, page_log)
    fast_learner.reset_memory()

    # First test without memory.
    page.add_lines("\nClear memory, then ask the question.")
    response = await fast_learner.handle_user_message(task_description)

    # Check the response.
    response_is_correct, extracted_answer = await grader.is_response_correct(task_description, response, answer)
    page.add_lines("Extracted answer:  {}".format(extracted_answer), flush=True)
    if response_is_correct:
        page.add_lines("Answer is CORRECT.\n", flush=True)
    else:
        page.add_lines("Answer is INCORRECT.\n", flush=True)

    # Give the advice.
    page.add_lines("Give the advice.")
    insight = "When somebody builds something on autogen and wants to contribute it to autogen, instead of creating a new autogen package, it's better for them to implement it in a separate github repo, then just add the autogen-extension topic to that repo. That way their contribution will be automatically discoverable through autogen's page on community extensions:  https://microsoft.github.io/autogen/dev/user-guide/extensions-user-guide/index.html"
    await fast_learner.handle_user_message(insight)

    # Now ask the question again to see if the advice is retrieved from memory.
    page.add_lines("\nAsk the question again to see if the advice is retrieved from memory.")
    response = await fast_learner.handle_user_message(task_description)

    # Check the response.
    response_is_correct, extracted_answer = await grader.is_response_correct(task_description, response, answer)
    page.add_lines("Extracted answer:  {}".format(extracted_answer), flush=True)
    if response_is_correct:
        page.add_lines("Answer is CORRECT.\n", flush=True)
    else:
        page.add_lines("Answer is INCORRECT.\n", flush=True)

    page_log.finish_page(page)


async def eval_learning_from_demonstration(fast_learner, evaluator, client, page_log, settings):
    """An evaluation"""
    page = page_log.begin_page(
        summary="eval_learning_from_demonstration",
        details='',
        method_call="eval_learning_from_demonstration")

    task_details = get_task_by_name("cell_towers")
    num_trials = settings["num_trials"]
    fast_learner.reset_memory()

    # Start by clearing memory then running a baseline test.
    page.add_lines("To get a baseline, clear memory, then assign the task.")
    num_successes, num_trials = await evaluator.test_fast_learner(
        fast_learner=fast_learner, task_details=task_details, num_trials=num_trials,
        use_memory=True, client=client, page_log=page_log)
    success_rate = round((num_successes / num_trials) * 100)
    page.add_lines("\nSuccess rate:  {}%\n".format(success_rate), flush=True)

    # Provide the demonstration.
    page.add_lines("Demonstrate a solution to a similar task.")
    demo_task = "You are a telecommunications engineer who wants to build cell phone towers on a stretch of road. Houses are located at mile markers 17, 20, 19, 10, 11, 12, 3, 6. Each cell phone tower can cover houses located next to the road within a 4-mile radius. Find the minimum number of cell phone towers needed to cover all houses next to the road. Your answer should be a positive numerical integer value."
    demonstration = "Sort the houses by location:  3, 6, 10, 11, 12, 17, 19, 20. Then start at one end and place the towers only where absolutely needed. The house at 3 could be served by a tower as far away as mile marker 7, because 3 + 4 = 7, so place a tower at 7. This obviously covers houses up to mile 7. But a coverage radius of 4 miles (in each direction) means a total coverage of 8 miles. So the tower at mile 7 would reach all the way to mile 11, covering the houses at 10 and 11. The next uncovered house would be at mile 12 (not 10), requiring a second tower. It could go at mile 16 (which is 12 + 4) and this tower would reach up to mile 20 (16 + 4), covering the remaining houses. So 2 towers would be enough."
    await fast_learner.learn_from_demonstration(demo_task, demonstration)

    # Now test again to see if the demonstration (retrieved from memory) helps.
    page.add_lines("Assign the task again to see if the demonstration helps.")
    num_successes, num_trials = await evaluator.test_fast_learner(
        fast_learner=fast_learner, task_details=task_details, num_trials=num_trials,
        use_memory=True, client=client, page_log=page_log)
    success_rate = round((num_successes / num_trials) * 100)
    page.add_lines("\nSuccess rate:  {}%\n".format(success_rate), flush=True)

    page_log.finish_page(page)


async def eval_self_teaching(fast_learner, evaluator, client, page_log, settings):
    """An evaluation"""
    page = page_log.begin_page(
        summary="eval_self_teaching",
        details='',
        method_call="eval_self_teaching")

    fast_learner.reset_memory()

    task_details_list = [get_task_by_name("10_liars"), get_task_by_name("100_vampires")]
    total_num_successes_list = [0 for _ in range(len(task_details_list))]
    total_num_trials = 0
    for i in range(settings["num_loops"]):
        # Always train on the first task in the list.
        task_details = task_details_list[0]
        await fast_learner.train_on_task(
            task=task_details["task_description"],
            expected_answer=task_details["expected_answer"])

        # Test on all tasks in the list.
        for j, task_details in enumerate(task_details_list):
            num_successes, num_trials = await evaluator.test_fast_learner(
                fast_learner=fast_learner, task_details=task_details, num_trials=settings["num_final_test_trials"],
                use_memory=True, client=client, page_log=page_log)

            page.add_lines("Success rate ({}):  {}%".format(j, round((num_successes / num_trials) * 100)), flush=True)
            total_num_successes_list[j] += num_successes
        total_num_trials += settings["num_final_test_trials"]
        page.add_lines("")

    for i, total_num_successes in enumerate(total_num_successes_list):
        success_rate = round((total_num_successes / total_num_trials) * 100)
        page.add_lines("\nOverall success rate ({}):  {}%\n".format(i, success_rate), flush=True)

    page_log.finish_page(page)


class Evaluator:
    def __init__(self):
        self.page_log = None
        self.client_creator = None

    async def test_fast_learner(self, fast_learner, task_details, num_trials, use_memory,
                   client, page_log) -> Tuple[int, int]:
        page = page_log.begin_page(
            summary="Evaluator.test_fast_learner",
            details='',
            method_call="Evaluator.test_fast_learner")

        page.add_lines("Testing the fast learner on the given task.\n", flush=True)

        grader = Grader(client, page_log)
        num_successes = 0

        for trial in range(num_trials):
            page.add_lines("\n-----  TRIAL {}  -----\n".format(trial + 1), flush=True)
            page.add_lines("Try to solve the task.\n", flush=True)
            task_description = task_details["task_description"]
            response = await fast_learner.assign_task(task_description, use_memory=use_memory)
            response_is_correct, extracted_answer = await grader.is_response_correct(
                task_description, response, task_details["expected_answer"])
            page.add_lines("Extracted answer:  {}".format(extracted_answer), flush=True)
            if response_is_correct:
                page.add_lines("Answer is CORRECT.\n", flush=True)
                num_successes += 1
            else:
                page.add_lines("Answer is INCORRECT.\n", flush=True)

        page.add_lines("\nSuccess rate:  {}%\n".format(round((num_successes / num_trials) * 100)), flush=True)
        page_log.finish_page(page)
        return num_successes, num_trials

    async def run(self, settings_filepath):
        # Load the settings from yaml.
        with open(settings_filepath, "r") as file:
            settings = yaml.load(file, Loader=yaml.FullLoader)
            evaluator_settings = settings["Evaluator"]

            # Create the PageLog.
            self.page_log = PageLog(evaluator_settings["PageLog"])
            page = self.page_log.begin_page(
                summary="Evaluator.main",
                details='',
                method_call="Evaluator.main")

            # Create the client, passed to both the fast_learner and the evaluator.
            client_creator = ClientCreator(settings=settings["client"], page_log=self.page_log)
            client = client_creator.create_client()

            # Create the specified fast_learner implementation.
            fast_learner_settings = settings["FastLearner"]
            module_path = fast_learner_settings["module_path"]
            try:
                module = importlib.import_module(module_path)
            except ModuleNotFoundError:
                print('Failed to import {}'.format(module_path))
                raise
            class_name = fast_learner_settings["class_name"]
            try:
                fast_learner_class = getattr(module, class_name)
            except AttributeError:
                print('Failed to import {}.{}'.format(module_path, class_name))
                raise
            try:
                fast_learner = fast_learner_class(fast_learner_settings, self, client, self.page_log)
            except Exception as err:
                print("Error creating \"{}\": {}".format(fast_learner_class, err))
                raise

            # Execute each evaluation.
            for evaluation in settings["evaluations"]:
                eval_function = globals()[evaluation["name"]]
                await eval_function(fast_learner, self, client, self.page_log, evaluation)

            if hasattr(client, "finalize"):
                # If this is a client wrapper, it needs to be finalized.
                client.finalize()

            self.page_log.flush(final=True)  # Finalize the page log
            self.page_log.finish_page(page)


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 1:
        print("Usage:  amt.py <path to *.yaml file>")
    else:
        evaluator = Evaluator()
        asyncio.run(evaluator.run(settings_filepath=args[0]))
