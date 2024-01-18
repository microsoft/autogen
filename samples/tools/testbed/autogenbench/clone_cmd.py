import os
import json
import argparse
import requests
from .load_module import load_module

# Figure out where everything is
SCRIPT_PATH = os.path.realpath(__file__)
SCRIPT_NAME = os.path.basename(SCRIPT_PATH)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)

# Where are the manifests located?
BRANCH = "autogenbench"
URL_PREFIX = f"https://raw.githubusercontent.com/microsoft/autogen/{BRANCH}/"
SCENARIOS = {
    "Examples": "samples/tools/testbed/scenarios/Examples/MANIFEST.json",
    "HumanEval": "samples/tools/testbed/scenarios/HumanEval/MANIFEST.json",
    "GAIA": "samples/tools/testbed/scenarios/GAIA/MANIFEST.json",
    "AutoGPT": "samples/tools/testbed/scenarios/AutoGPT/MANIFEST.json",
    "MATH": "samples/tools/testbed/scenarios/MATH/MANIFEST.json",
}


def get_scenarios():
    """
    Return a list of scenarios.
    """
    return SCENARIOS.keys()


def _expand_url(url_fragment):
    """
    If the url is a relative path, append the URL_PREFIX, otherwise return it whole.
    """
    if url_fragment.startswith("http://") or url_fragment.startswith("https://"):
        return url_fragment
    else:
        return URL_PREFIX + url_fragment


def clone_scenario(scenario):
    if scenario not in get_scenarios():
        raise ValueError(f"No such scenario '{scenario}'.")

    # Download the manifest
    print("Fetching manifest...")
    manifest = None
    response = requests.get(_expand_url(SCENARIOS[scenario]), stream=False)
    response.raise_for_status()
    manifest = json.loads(response.text)

    # Download the files
    for item in manifest["files"].items():
        path = item[0]
        raw_url = _expand_url(item[1])
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


def clone_cli(args):
    invocation_cmd = args[0]
    args = args[1:]

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

    parsed_args = parser.parse_args(args)

    # Check if we are just printing a list
    if parsed_args.list:
        print("The following scenarios / benchmarks are available:\n")
        for s in get_scenarios():
            print(f"  {s}")
        print()
        return 0

    if not parsed_args.scenario:
        parser.error("the following arguments are required: scenario")

    try:
        clone_scenario(parsed_args.scenario)
    except ValueError as e:
        parser.error(str(e) + "\nUse '--list' to see a list of available scenarios.")
