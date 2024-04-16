import argparse
import json
import os

import requests

from .load_module import load_module

# Figure out where everything is
SCRIPT_PATH = os.path.realpath(__file__)
SCRIPT_NAME = os.path.basename(SCRIPT_PATH)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)

# Where are the manifests located?
DEFAULT_REPO = "https://raw.githubusercontent.com/microsoft/autogen/"
DEFAULT_BRANCH = "main"
DEFAULT_PATH = "/samples/tools/autogenbench/scenarios/"
# Full url is specified by DEFAULT_REPO + DEFAULT_BRANCH + DEFAULT_PATH


def _expand_url(url_fragment, base_url):
    """
    If the url is a relative path, append the URL_PREFIX, otherwise return it whole.
    """
    if url_fragment.startswith("http://") or url_fragment.startswith("https://"):
        return url_fragment
    else:
        return base_url + url_fragment


def get_scenarios(base_url):
    """
    Return a list of scenarios.
    """
    response = requests.get(_expand_url("MANIFEST.json", base_url), stream=False)
    response.raise_for_status()
    manifest = json.loads(response.text)
    return manifest["scenarios"]


def clone_scenario(scenario, base_url):
    # If the scenario is a url, then we can just look up that folder directly
    if scenario.startswith("http://") or scenario.startswith("https://"):
        scenario_url = scenario
        local_folder = os.path.abspath(".")
    # otherwise, read it from the main manifest file
    else:
        scenarios = get_scenarios(base_url)
        if scenario not in scenarios:
            raise ValueError(f"No such scenario '{scenario}'.")
        scenario_url = _expand_url(scenarios[scenario], base_url)
        local_folder = os.path.abspath(scenario)

    # Download the manifest
    print("Fetching manifest...")
    manifest = None
    response = requests.get(_expand_url("MANIFEST.json", scenario_url), stream=False)
    response.raise_for_status()
    manifest = json.loads(response.text)

    # Download the files
    for item in manifest["files"].items():
        path = item[0]

        # Fixes paths on windows
        parts = path.split("/")
        path = os.path.join(*parts)

        raw_url = _expand_url(item[1], scenario_url)
        dir_name = os.path.join(local_folder, os.path.dirname(path))
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
    init_tasks_script = os.path.join(local_folder, "Scripts", "init_tasks.py")
    if os.path.isfile(init_tasks_script):
        load_module(init_tasks_script).main()

    # Print the success
    print(f"\n\nSuccessfully cloned '{scenario}'")
    for readme in ["README.md", "README.txt", "README"]:
        if os.path.isfile(os.path.join(local_folder, readme)):
            print(f"Please read '{os.path.join(local_folder, readme)}' for more information on running this benchmark.")
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
    parser.add_argument(
        "-b",
        "--branch",
        type=str,
        help=f"The specific branch in the AutoGen GitHub repository from which scenarios will be cloned (default: {DEFAULT_BRANCH}).",
        default=DEFAULT_BRANCH,
    )

    parsed_args = parser.parse_args(args)

    # Generate the base_url
    base_url = DEFAULT_REPO + parsed_args.branch + DEFAULT_PATH

    # Check if we are just printing a list
    if parsed_args.list:
        print("The following scenarios / benchmarks are available:\n")
        for s in get_scenarios(base_url):
            print(f"  {s}")
        print()
        return 0

    if not parsed_args.scenario:
        parser.error("the following arguments are required: scenario")

    try:
        clone_scenario(parsed_args.scenario, base_url)
    except ValueError as e:
        parser.error(str(e) + "\nUse '--list' to see a list of available scenarios.")
