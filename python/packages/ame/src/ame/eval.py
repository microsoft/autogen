import sys, os
import yaml
import asyncio
import importlib
from typing import Tuple
from autogen_ext.apprentice import PageLog, Grader
from ame.clients._client_creator import ClientCreator


class Evaluator:
    def __init__(self):
        self.page_log = None

    def get_task_details_by_name(self, task_name):
        path_to_this_file = os.path.abspath(__file__)
        dir_of_this_file = os.path.dirname(path_to_this_file)
        task_filepath = os.path.join(dir_of_this_file, 'tasks', task_name + '.yaml')
        with open(task_filepath, "r") as file:
            task_details = yaml.load(file, Loader=yaml.FullLoader)
            assert task_details["name"] == task_name
            return task_details

    async def test_fast_learner(self, fast_learner, task_details, num_trials,
                                use_memory, client, page_log) -> Tuple[int, int]:
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
            fast_learner_settings = settings["fast_learning_agent"]
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
            for evaluation_settings in settings["evaluations"]:
                module_path = evaluation_settings["module_path"]
                try:
                    module = importlib.import_module(module_path)
                except ModuleNotFoundError:
                    print('Failed to import {}'.format(module_path))
                    raise
                function_name = evaluation_settings["function_name"]
                try:
                    eval_function = getattr(module, function_name)
                except AttributeError:
                    print('Failed to import {}.{}'.format(module_path, function_name))
                    raise
                await eval_function(fast_learner, self, client, self.page_log, evaluation_settings)

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
