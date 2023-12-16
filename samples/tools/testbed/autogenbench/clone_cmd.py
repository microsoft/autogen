import os
import json
import sys
import argparse
import requests
import importlib.util

# Figure out where everything is
SCRIPT_PATH = os.path.realpath(__file__)
SCRIPT_NAME = os.path.basename(SCRIPT_PATH)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)

SCENARIO_PATH = os.path.join(SCRIPT_DIR, "scenarios")


def load_module(module_path):
    module_name = os.path.basename(module_path).replace(".py", "")
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def get_scenarios():
    """
    Return a list of scenarios.
    """
    return [
        f
        for f in os.listdir(SCENARIO_PATH)
        if os.path.isfile(os.path.join(SCENARIO_PATH, f))
    ]


def clone_scenario(scenario):
    if scenario not in get_scenarios():
        raise ValueError(f"No such scenario '{scenario}'.")

    # Read the scenario
    manifest = None
    with open(os.path.join(SCENARIO_PATH, scenario), "rt") as fh:
        manifest = json.loads(fh.read())

    # Download the files
    for item in manifest["files"].items():
        path = item[0]
        raw_url = item[1]
        dir_name = os.path.join(scenario, os.path.dirname(path))
        file_name = os.path.basename(path)
        path = os.path.join(dir_name, file_name)

        print(f"'{raw_url}' -> '{path}'")

        # Make the directory
        os.makedirs(dir_name, exist_ok=True)

        # Send a HTTP request to the URL
        response = requests.get(raw_url, stream=True)
        response.raise_for_status()

        # If the HTTP request returns a status code 200, proceed
        if response.status_code == 200:
            with open(path, "wb") as fh:
                for chunk in response.iter_content(chunk_size=512):
                    fh.write(chunk)
        else:
            pass
            # Raise an Error

    # Run any post-download scripts
    download_script = os.path.join(scenario, "Scripts", "download.py")
    if os.path.isfile(download_script):
        load_module(download_script).main()

    # Print the success
    print(f"\n\nSuccessfully cloned '{scenario}'")
    for readme in ["README.md", "README.txt", "README"]:
        if os.path.isfile(os.path.join(scenario, readme)):
            print(
                f"Please read '{os.path.join(scenario, readme)}' for more information on running this benchmark."
            )
            break


def clone_cli(invocation_cmd="autogenbench clone", cli_args=None):
    # Prepare the argument parser
    parser = argparse.ArgumentParser(
        prog=invocation_cmd,
        description=f"{invocation_cmd} will clone the specified scenarios to the local directory.",
    )

    parser.add_argument(
        "scenario",
        help="The name of the scenario clone.",
    )
    parser.add_argument(
        "-l",
        "--list",
        action="store_true",
        help="List the scenarios available for download.",
    )

    # In most cases just parse args from sys.arv[1:], which is the parse_args default
    args = None
    if cli_args is None:
        args = parser.parse_args()
    else:
        args = parser.parse_args(cli_args)

    # Chekc if we are just printing a list
    if args.list:
        for s in get_scenarios():
            print(s)
        return 0

    try:
        clone_scenario(args.scenario)
    except ValueError as e:
        sys.exit(str(e) + "\nUse '--list' to see a list of available scenarios.")
