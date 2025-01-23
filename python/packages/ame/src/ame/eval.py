import asyncio
import importlib
import os
import sys
from typing import Tuple

import yaml
from autogen_ext.apprentice import Grader, PageLogger

from ame.clients._client_creator import ClientCreator


class Evaluator:
    def __init__(self):
        self.logger = None

    def get_task_description_and_answer_from_file(self, task_filename):
        path_to_this_file = os.path.abspath(__file__)
        dir_of_this_file = os.path.dirname(path_to_this_file)
        task_filepath = os.path.join(dir_of_this_file, "task_data", "tasks", task_filename + ".yaml")
        with open(task_filepath, "r") as file:
            task_details = yaml.load(file, Loader=yaml.FullLoader)
            return task_details["task_description"], task_details["expected_answer"]

    def get_advice_from_file(self, advice_filename):
        path_to_this_file = os.path.abspath(__file__)
        dir_of_this_file = os.path.dirname(path_to_this_file)
        task_filepath = os.path.join(dir_of_this_file, "task_data", "advice", advice_filename + ".yaml")
        with open(task_filepath, "r") as file:
            advice_dict = yaml.load(file, Loader=yaml.FullLoader)
            return advice_dict["advice"]

    def get_demo_from_file(self, demo_filename):
        path_to_this_file = os.path.abspath(__file__)
        dir_of_this_file = os.path.dirname(path_to_this_file)
        task_filepath = os.path.join(dir_of_this_file, "task_data", "demos", demo_filename + ".yaml")
        with open(task_filepath, "r") as file:
            demo_dict = yaml.load(file, Loader=yaml.FullLoader)
            return demo_dict["demo"]

    async def test_fast_learner(
        self, fast_learner, task_description, expected_answer, num_trials, use_memory, client, logger
    ) -> Tuple[int, int]:
        logger.enter_function()

        self.logger.info("Testing the fast learner on the given task.\n")

        grader = Grader(client, logger)
        num_successes = 0

        for trial in range(num_trials):
            self.logger.info("\n-----  TRIAL {}  -----\n".format(trial + 1))
            self.logger.info("Try to solve the task.\n")
            response = await fast_learner.assign_task(task_description, use_memory=use_memory)
            response_is_correct, extracted_answer = await grader.is_response_correct(
                task_description, response, expected_answer
            )
            self.logger.info("Extracted answer:  {}".format(extracted_answer))
            if response_is_correct:
                self.logger.info("Answer is CORRECT.\n")
                num_successes += 1
            else:
                self.logger.info("Answer is INCORRECT.\n")

        self.logger.info("\nSuccess rate:  {}%\n".format(round((num_successes / num_trials) * 100)))
        logger.leave_function()
        return num_successes, num_trials

    async def perform_evaluations(self, settings):
        self.logger.enter_function()

        # Create the client, passed to both the fast_learner and the evaluator.
        client_creator = ClientCreator(settings=settings["client"], logger=self.logger)
        client = client_creator.create_client()

        # Create the specified fast_learner implementation.
        fast_learner_settings = settings["fast_learning_agent"]
        module_path = fast_learner_settings["module_path"]
        try:
            module = importlib.import_module(module_path)
        except ModuleNotFoundError:
            print("Failed to import {}".format(module_path))
            raise
        class_name = fast_learner_settings["class_name"]
        try:
            fast_learner_class = getattr(module, class_name)
        except AttributeError:
            print("Failed to import {}.{}".format(module_path, class_name))
            raise
        try:
            fast_learner = fast_learner_class(fast_learner_settings, self, client, self.logger)
        except Exception as err:
            print('Error creating "{}": {}'.format(fast_learner_class, err))
            raise

        # Execute each evaluation.
        for evaluation_settings in settings["evaluations"]:
            # Import the function.
            function_settings = evaluation_settings["eval_function"]
            module_path = function_settings["module_path"]
            try:
                module = importlib.import_module(module_path)
            except ModuleNotFoundError:
                print("Failed to import {}".format(module_path))
                raise
            function_name = function_settings["function_name"]
            try:
                eval_function = getattr(module, function_name)
            except AttributeError:
                print("Failed to import {}.{}".format(module_path, function_name))
                raise

            # Call the eval function for each listed run.
            for run_dict in evaluation_settings["runs"]:
                results = await eval_function(fast_learner, self, client, self.logger, function_settings, run_dict)
                print(results)

        if hasattr(client, "finalize"):
            # If this is a client wrapper, it needs to be finalized.
            client.finalize()

        self.logger.flush(finished=True)
        self.logger.leave_function()

    async def run(self, settings_filepath):
        # Load the settings from yaml.
        with open(settings_filepath, "r") as file:
            settings = yaml.load(file, Loader=yaml.FullLoader)
            evaluator_settings = settings["Evaluator"]
            self.logger = PageLogger(evaluator_settings["PageLogger"])

            # Perform the evaluations.
            await self.perform_evaluations(settings)


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 1:
        print("Usage:  amt.py <path to *.yaml file>")
    else:
        evaluator = Evaluator()
        asyncio.run(evaluator.run(settings_filepath=args[0]))
