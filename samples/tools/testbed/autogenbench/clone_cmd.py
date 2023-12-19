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

# Where are the manifests located?
BRANCH = "testbed_cli"
SCENARIOS = {
    "Examples": f"https://raw.githubusercontent.com/microsoft/autogen/{BRANCH}/samples/tools/testbed/scenarios/Examples/MANIFEST.json",
    "HumanEval": f"https://raw.githubusercontent.com/microsoft/autogen/{BRANCH}/samples/tools/testbed/scenarios/HumanEval/MANIFEST.json",
    "GAIA": f"https://raw.githubusercontent.com/microsoft/autogen/{BRANCH}/samples/tools/testbed/scenarios/GAIA/MANIFEST.json",
    "AutoGPT": f"https://raw.githubusercontent.com/microsoft/autogen/{BRANCH}/samples/tools/testbed/scenarios/AutoGPT/MANIFEST.json",
    "MATH": f"https://raw.githubusercontent.com/microsoft/autogen/{BRANCH}/samples/tools/testbed/scenarios/MATH/MANIFEST.json",
}


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
    return SCENARIOS.keys()


def clone_scenario(scenario):
    if scenario not in get_scenarios():
        raise ValueError(f"No such scenario '{scenario}'.")

    # Download the manifest
    print("Fetching manifest...")
    manifest = None
    response = requests.get(SCENARIOS[scenario], stream=False)
    response.raise_for_status()
    manifest = json.loads(response.text)

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
        with open(path, "wb") as fh:
            for chunk in response.iter_content(chunk_size=512):
                fh.write(chunk)

    # Run any init_tasks scripts
    init_tasks_script = os.path.join(scenario, "Scripts", "init_tasks.py")
    if os.path.isfile(init_tasks_script):
        load_module(init_tasks_script).main()

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
        description=f"{invocation_cmd} will clone the specified scenario to the current working directory.",
    )

    parser.add_argument(
        "scenario",
        nargs="?",
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
        print("The following scenarios / benchmarks are available:\n")
        for s in get_scenarios():
            print(f"  {s}")
        print()
        return 0

    if not args.scenario:
        parser.error("the following arguments are required: scenario")

    try:
        clone_scenario(args.scenario)
    except ValueError as e:
        parser.error(str(e) + "\nUse '--list' to see a list of available scenarios.")
