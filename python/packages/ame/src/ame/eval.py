import asyncio
import importlib
import sys
import yaml

from autogen_ext.agentic_memory import PageLogger, Apprentice
from ame.clients._client_creator import ClientCreator


async def perform_evaluations(settings, logger) -> None:
    """
    Perform the evaluations as specified in the settings file.
    """
    logger.enter_function()

    # Create the client.
    client_creator = ClientCreator(settings=settings["client"], logger=logger)
    client = client_creator.create_client()

    # Create the apprentice.
    apprentice_settings = settings["Apprentice"]
    apprentice = Apprentice(apprentice_settings, client, logger)

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
            results = await eval_function(apprentice, client, logger, function_settings, run_dict)
            print(results)

    if hasattr(client, "finalize"):
        # If this is a client wrapper, it needs to be finalized.
        client.finalize()

    logger.flush(finished=True)
    logger.leave_function()


async def run(settings_filepath):
    # Load the settings from yaml.
    with open(settings_filepath, "r") as file:
        settings = yaml.load(file, Loader=yaml.FullLoader)
        logger = PageLogger(settings["PageLogger"])

        # Perform the evaluations.
        await perform_evaluations(settings, logger)


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) != 1:
        print("Usage:  amt.py <path to *.yaml file>")
    else:
        asyncio.run(run(settings_filepath=args[0]))
