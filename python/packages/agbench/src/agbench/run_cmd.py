import argparse
import errno
import json
import logging
import os
import pathlib
import random
import re
import shutil
import subprocess
import sys
import time
import traceback
from multiprocessing import Pool
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple, Union, cast

import docker
import yaml
from azure.core.exceptions import ClientAuthenticationError
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from docker.errors import APIError, DockerException, ImageNotFound
from typing_extensions import TypedDict

from .version import __version__

# Figure out where everything is
SCRIPT_PATH = os.path.realpath(__file__)
SCRIPT_NAME = os.path.basename(SCRIPT_PATH)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)

TASK_TIMEOUT = 60 * 120  # 120 minutes

BASE_TEMPLATE_PATH = os.path.join(SCRIPT_DIR, "template")
RESOURCES_PATH = os.path.join(SCRIPT_DIR, "res")

# What platform are we running?
IS_WIN32 = sys.platform == "win32"

# This is the tag given to the image that is *built* when no other image is provided.
# Do not use this field to specify the name of an existing image (e.g., on Dockerhub)
DEFAULT_DOCKER_IMAGE_TAG = "agbench"

DEFAULT_ENV_FILE_JSON = "ENV.json"
DEFAULT_ENV_FILE_YAML = "ENV.yaml"
DEFAULT_CONFIG_YAML = "config.yaml"

# Get a random number generator for subsampling
subsample_rng = random.Random(425)


class ScenarioInstance(TypedDict):
    id: str
    template: Union[str, List[Union[str, List[str]]]]
    substitutions: Dict[str, Dict[str, str]]
    values: Dict[str, Dict[str, str]]


def run_scenarios(
    scenario: str,
    n_repeats: int,
    is_native: bool,
    config_file: Union[None, str],
    token_provider: Optional[Callable[[], str]],
    docker_image: Optional[str] = None,
    results_dir: str = "Results",
    subsample: Union[None, int, float] = None,
    env_file: Union[None, str] = None,
) -> None:
    """
    Run a set agbench scenarios a given number of times.

    Args:
        scenario (path):    The file or folder containing the scenario JSONL instances. If given a folder, then
                            all JSONL files in the folder will be loaded and run.
        n_repeats (int):    The number of times each scenario instance will be repeated
        is_native (bool):   True if the scenario should be run locally rather than in Docker (proceed with caution!)
        results_dir (path): The folder were results will be saved.
    """

    files: List[str] = []

    # Figure out which files or folders we are working with
    if scenario == "-" or os.path.isfile(scenario):
        files.append(scenario)
    elif os.path.isdir(scenario):
        for f in os.listdir(scenario):
            scenario_file = os.path.join(scenario, f)

            if not os.path.isfile(scenario_file):
                continue

            if not scenario_file.lower().endswith(".jsonl"):
                continue

            files.append(scenario_file)
    else:
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), scenario)

    # Run all the scenario files
    for scenario_file in files:
        scenario_name: Optional[str] = None
        scenario_dir: Optional[str] = None
        file_handle = None

        # stdin
        if scenario_file == "-":
            scenario_name = "stdin"
            scenario_dir = "."
            file_handle = sys.stdin
        else:
            scenario_name_parts = os.path.basename(scenario_file).split(".")
            scenario_name_parts.pop()
            scenario_name = ".".join(scenario_name_parts)
            scenario_dir = os.path.dirname(os.path.realpath(scenario_file))
            file_handle = open(scenario_file, "rt")

        # Read all the lines, then subsample if needed
        lines = [line for line in file_handle]
        if subsample is not None:
            # How many lines are we sampling
            n = 0
            # It's a proportion
            if 0 <= subsample < 1:
                n = int(len(lines) * subsample + 0.5)
            # It's a raw count
            else:
                n = int(subsample)
            n = max(0, min(n, len(lines)))
            lines = subsample_rng.sample(lines, n)

        for line in lines:
            instance = json.loads(line)

            # Create a folder to store the results
            # Results base
            if not os.path.isdir(results_dir):
                os.mkdir(results_dir)

            # Results for the scenario
            results_scenario = os.path.join(results_dir, scenario_name)
            if not os.path.isdir(results_scenario):
                os.mkdir(results_scenario)

            # Results for the instance
            results_instance = os.path.join(results_scenario, instance["id"])
            if not os.path.isdir(results_instance):
                os.mkdir(results_instance)

            # Results for the repeats
            for i in range(0, n_repeats):
                results_repetition = os.path.join(results_instance, str(i))

                # Skip it if it already exists
                if os.path.isdir(results_repetition):
                    print(f"Found folder {results_repetition} ... Skipping.")
                    continue
                print(f"Running scenario {results_repetition}")

                # Expand the scenario
                expand_scenario(scenario_dir, instance, results_repetition, config_file)

                # Prepare the environment (keys/values that need to be added)
                env = get_scenario_env(token_provider=token_provider, env_file=env_file)

                # Run the scenario
                if is_native:
                    run_scenario_natively(results_repetition, env)
                else:
                    run_scenario_in_docker(
                        results_repetition,
                        env,
                        docker_image=docker_image,
                    )

        # Close regular files
        if scenario_file != "-":
            file_handle.close()


def expand_scenario(
    scenario_dir: str, scenario: ScenarioInstance, output_dir: str, config_file: Union[str, None]
) -> None:
    """
    Expand a scenario into a folder.
    Despite some awkwardness created by backwards compatibility and notational conveniences, expansion is conceptually simple.
    It is a series of copy commands (similar to `cp -R`), followed by a series of in-place fine and replace operations.
    """

    template = scenario["template"]

    # Either key works for finding the substiturions list. "values" may be deprecated in the future
    substitutions = scenario["substitutions"] if "substitutions" in scenario else scenario["values"]

    # Older versions are only one-level deep. Convert them,
    if len(substitutions) > 0 and isinstance(substitutions[next(iter(substitutions))], str):
        substitutions = {"scenario.py": cast(Dict[str, str], substitutions)}

    copy_operations: List[Tuple[str, str]] = []

    # Handle file (str), folder (str), or mapping (List) templates
    if isinstance(template, str):
        template_path = os.path.join(scenario_dir, template)
        if os.path.isdir(template_path):
            copy_operations.append((template, ""))
        else:
            copy_operations.append((template, "scenario.py"))
    elif isinstance(template, list):
        for elm in template:
            if isinstance(elm, list):
                copy_operations.append((elm[0], elm[1]))
            else:
                copy_operations.append((elm, ""))
    else:
        raise ValueError("expand_scenario expects an str or list for 'template'")

    # The global includes folder is always copied
    shutil.copytree(
        BASE_TEMPLATE_PATH,
        output_dir,
        ignore=shutil.ignore_patterns("*.example"),
        dirs_exist_ok=False,
    )

    # Expand other folders
    for items in copy_operations:
        src_path = pathlib.Path(os.path.join(scenario_dir, items[0])).absolute()
        dest_path = pathlib.Path(os.path.join(output_dir, items[1])).absolute()

        if os.path.isdir(src_path):
            shutil.copytree(src_path, dest_path, dirs_exist_ok=True)
        else:
            if os.path.isdir(dest_path):
                # If the destination is a directory, use the same filename
                shutil.copyfile(src_path, os.path.join(dest_path, os.path.basename(src_path)))
            else:
                # Otherwuse use the filename provided
                shutil.copyfile(src_path, dest_path)

    # Expand templated files
    for templated_file in substitutions.keys():  # Keys are relative file paths
        # Read the templated file into memory
        template_contents: List[str] = list()
        with open(os.path.join(output_dir, templated_file), "rt") as fh:
            for line in fh:
                template_contents.append(line)

        # Rewrite the templated file with substitutions
        values = substitutions[templated_file]
        with open(os.path.join(output_dir, templated_file), "wt") as fh:
            for line in template_contents:
                for k, v in values.items():
                    line = line.replace(k, v)
                fh.write(line)

    # Copy the config
    if config_file is None:
        if os.path.isfile(DEFAULT_CONFIG_YAML):
            config_file = DEFAULT_CONFIG_YAML

    if config_file is not None:
        src_path = pathlib.Path(config_file).absolute()
        dest_path = pathlib.Path(os.path.join(output_dir, "config.yaml")).absolute()
        shutil.copyfile(src_path, dest_path)
    else:
        logging.warning(f"No {DEFAULT_CONFIG_YAML} file found.")


def get_scenario_env(token_provider: Optional[Callable[[], str]] = None, env_file: str | None = None) -> Dict[str, str]:
    """
    Return a dictionary of environment variables needed to run a scenario.

    Args:
        config_list (list): An AutoGen OAI_CONFIG_LIST to be used when running scenarios.
        env_file (str): The path to the env_file to read. (if None, default to DEFAULT_ENV_FILE)

    Returns: A dictionary of keys and values that need to be added to the system environment.
    """
    env: Dict[str, str] = dict()

    # Populate with commonly needed keys
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if openai_api_key is not None and len(openai_api_key.strip()) > 0:
        env["OPENAI_API_KEY"] = openai_api_key

    ## Support Azure auth tokens
    azure_openai_ad_token = os.environ.get("AZURE_OPENAI_AD_TOKEN")
    if azure_openai_ad_token is None and token_provider is not None:
        azure_openai_ad_token = token_provider()
    if azure_openai_ad_token is not None and len(azure_openai_ad_token.strip()) > 0:
        env["AZURE_OPENAI_AD_TOKEN"] = azure_openai_ad_token

    # Update with any values from the ENV.json file
    env_file_contents: Dict[str, Any] = {}
    if env_file is None:
        # Env file was not specified, so read the default, or warn if the default file is missing.
        if os.path.isfile(DEFAULT_ENV_FILE_YAML):
            with open(DEFAULT_ENV_FILE_YAML, "r") as fh:
                env_file_contents = yaml.safe_load(fh)
        elif os.path.isfile(DEFAULT_ENV_FILE_JSON):
            with open(DEFAULT_ENV_FILE_JSON, "rt") as fh:
                env_file_contents = json.loads(fh.read())
            logging.warning(f"JSON environment files are deprecated. Migrate to '{DEFAULT_ENV_FILE_YAML}'")
        else:
            logging.warning(
                f"The environment file '{DEFAULT_ENV_FILE_YAML}' was not found. A default environment will be provided, containing the keys: {env.keys()}"
            )
    else:
        # Env file was specified. Throw an error if the file can't be read.
        with open(env_file, "rt") as fh:
            if env_file.endswith(".json"):
                logging.warning("JSON environment files are deprecated. Migrate to YAML")
                env_file_contents = json.loads(fh.read())
            else:
                env_file_contents = yaml.safe_load(fh)

    # Apply substitutions in-place
    substitute_env_variables(env_file_contents)

    # Flatten any structures
    for key, value in env_file_contents.items():
        if isinstance(value, dict) or isinstance(value, list):
            env_file_contents[key] = json.dumps(value)

    # Warn about carrying env variables
    if "OPENAI_API_KEY" in env and "OPENAI_API_KEY" not in env_file_contents:
        logging.warning(
            f"Implicit inclusion of OPENAI_API_KEY in the task environment is deprecated. Add it to {DEFAULT_ENV_FILE_YAML} instead. E.g.,\n"
            + """

OPENAI_API_KEY: ${OPENAI_API_KEY}

"""
        )

    # Apply the loaded variables
    env.update(cast(Dict[str, str], env_file_contents))

    return env


def substitute_env_variables(json_data: Any) -> None:
    """
    Recursively replaces any instance of "${ENV_VARIABLE}" with os.environ("ENV_VARIABLE") in a structure returned from json.loads()
    """

    def replace_env_var(match: Any) -> str:
        var_name = match.group(1)
        return os.environ.get(var_name, "")

    pattern = re.compile(r"\$\{(\w+)\}")

    def replace_in_dict(d: Dict[str, Any]) -> None:
        for key, value in d.items():
            if isinstance(value, str):
                d[key] = pattern.sub(replace_env_var, value)
            elif isinstance(value, dict):
                replace_in_dict(cast(Dict[str, Any], value))
            elif isinstance(value, list):
                # Note: with the task mypy complains of a redundant cast
                # without the cast, pyright complains the type is unknown
                replace_in_list(cast(List[Any], value))  # type: ignore

    def replace_in_list(lst: List[Any]) -> None:
        for i, item in enumerate(lst):
            if isinstance(item, str):
                lst[i] = pattern.sub(replace_env_var, item)
            elif isinstance(item, dict):
                replace_in_dict(cast(Dict[str, Any], item))
            elif isinstance(item, list):
                replace_in_list(cast(List[Any], item))  # type: ignore

    if isinstance(json_data, dict):
        replace_in_dict(cast(Dict[str, Any], json_data))
    elif isinstance(json_data, list):
        replace_in_list(cast(List[Any], json_data))  # type: ignore


def run_scenario_natively(work_dir: str, env: Mapping[str, str], timeout: int = TASK_TIMEOUT) -> None:
    """
    Run a scenario in the native environment.

    Args:
        work_dir (path): the path to the working directory previously created to house this sceario instance
    """

    # Get the current working directory
    cwd = os.getcwd()

    # Prepare the environment variables
    full_env = os.environ.copy()
    full_env.update(env)

    # Navigate to the scenario
    os.chdir(work_dir)
    print("\n\n" + os.getcwd() + "\n===================================================================")

    # Prepare the run script
    with open(os.path.join("run.sh"), "wt") as f:
        f.write(
            f"""#
echo RUN.SH STARTING !#!#
export AUTOGEN_TESTBED_SETTING="Native"
echo "agbench version: {__version__}" > timestamp.txt

# Create and activate the virtual environment
# This is called in a subprocess, and will not impact the parent
{sys.executable} -m venv .agbench_venv
. .agbench_venv/bin/activate

# Run the global init script if it exists
if [ -f global_init.sh ] ; then
    . ./global_init.sh
fi

# Run the scenario init script if it exists
if [ -f scenario_init.sh ] ; then
    . ./scenario_init.sh
fi

# Run the scenario
pip install -r requirements.txt
echo SCENARIO.PY STARTING !#!#
start_time=$(date +%s)
timeout --preserve-status --kill-after {timeout  + 30}s {timeout}s python scenario.py
end_time=$(date +%s)
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo SCENARIO.PY EXITED WITH CODE: $EXIT_CODE !#!#
else
    echo SCENARIO.PY COMPLETE !#!#
fi
elapsed_time=$((end_time - start_time))
echo "SCENARIO.PY RUNTIME: $elapsed_time !#!#"

# Clean up
if [ -d .cache ] ; then
    rm -Rf .cache
fi

if [ -d __pycache__ ] ; then
    rm -Rf __pycache__
fi

# Run the scenario finalize script if it exists
if [ -f scenario_finalize.sh ] ; then
    . ./scenario_finalize.sh
fi

# Run the global finalize script if it exists
if [ -f global_finalize.sh ] ; then
    . ./global_finalize.sh
fi

# We don't need to deactivate the venv because it's
# contained in the subprocess; but we should clean it up
if [ -d .agbench_venv ] ; then
    rm -Rf .agbench_venv
fi

echo RUN.SH COMPLETE !#!#
"""
        )

    # Run the script and log the output
    with open("console_log.txt", "wb") as f:
        process = subprocess.Popen(
            ["sh", "run.sh"],
            env=full_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        for c in iter(lambda: process.stdout.read(1), b""):  # type: ignore
            f.write(c)
            os.write(sys.stdout.fileno(), c)  # Write binary to stdout

    # Return where we started
    os.chdir(cwd)
    return


def run_scenario_in_docker(
    work_dir: str, env: Mapping[str, str], timeout: int = TASK_TIMEOUT, docker_image: Optional[str] = None
) -> None:
    """
    Run a scenario in a Docker environment.

    Args:
        work_dir (path): the path to the working directory previously created to house this sceario instance
        timeout (Optional, int): the number of seconds to allow a Docker container to run before timing out
    """

    client = docker.from_env()
    image = None

    # If the docker_image is None, then we will fetch DEFAULT_DOCKER_IMAGE_TAG, if present,
    # or build it if missing.
    if docker_image is None:
        # Pull a suitable image
        try:
            image = client.images.get(DEFAULT_DOCKER_IMAGE_TAG)
        except ImageNotFound:
            print(f"Building default Docker image '{DEFAULT_DOCKER_IMAGE_TAG}'. This may take a few minutes...")
            try:
                build_default_docker_image(client, DEFAULT_DOCKER_IMAGE_TAG)
                image = client.images.get(DEFAULT_DOCKER_IMAGE_TAG)
            except DockerException:
                print(f"Failed to build image '{DEFAULT_DOCKER_IMAGE_TAG}'")

    # Otherwise get the requested image
    else:
        try:
            image = client.images.get(docker_image)
        except ImageNotFound:
            # pull the image
            print(f"Pulling image '{docker_image}'")
            try:
                image = client.images.pull(docker_image)
            except DockerException:
                print(f"Failed to pull image '{docker_image}'")

    # Prepare the run script
    with open(os.path.join(work_dir, "run.sh"), "wt", newline="\n") as f:
        f.write(
            f"""#
echo RUN.SH STARTING !#!#
export AUTOGEN_TESTBED_SETTING="Docker"

umask 000
echo "agbench version: {__version__}" > timestamp.txt

# Run the global init script if it exists
if [ -f global_init.sh ] ; then
    . ./global_init.sh
fi

# Run the scenario init script if it exists
if [ -f scenario_init.sh ] ; then
    . ./scenario_init.sh
fi

# Run the scenario
pip install -r requirements.txt
echo SCENARIO.PY STARTING !#!#
start_time=$(date +%s)
timeout --preserve-status --kill-after {timeout  + 30}s {timeout}s python scenario.py
end_time=$(date +%s)
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo SCENARIO.PY EXITED WITH CODE: $EXIT_CODE !#!#
else
    echo SCENARIO.PY COMPLETE !#!#
fi
elapsed_time=$((end_time - start_time))
echo "SCENARIO.PY RUNTIME: $elapsed_time !#!#"

# Clean up
if [ -d .cache ] ; then
    rm -Rf .cache
fi

if [ -d __pycache__ ] ; then
    rm -Rf __pycache__
fi

# Run the scenario finalize script if it exists
if [ -f scenario_finalize.sh ] ; then
    . ./scenario_finalize.sh
fi

# Run the global finalize script if it exists
if [ -f global_finalize.sh ] ; then
    . ./global_finalize.sh
fi

echo RUN.SH COMPLETE !#!#
"""
        )

    # Figure out what folders to mount
    volumes = {str(pathlib.Path(work_dir).absolute()): {"bind": "/workspace", "mode": "rw"}}

    # Add the autogen repo if we can find it
    autogen_repo_base = os.environ.get("AUTOGEN_REPO_BASE")
    if autogen_repo_base is None:
        autogen_repo_base = find_autogen_repo(os.getcwd())
    elif not os.path.isdir(autogen_repo_base):
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), autogen_repo_base)

    if autogen_repo_base is None:
        raise ValueError(
            "Could not find AutoGen repo base. Please set the environment variable AUTOGEN_REPO_BASE to the correct value."
        )

    autogen_repo_base = os.path.join(autogen_repo_base, "python")
    volumes[str(pathlib.Path(autogen_repo_base).absolute())] = {"bind": "/autogen_python", "mode": "rw"}

    print("Mounting:")
    for k in volumes:
        bind = volumes[k]["bind"]
        mode = volumes[k]["mode"].upper()
        if bind == "/workspace":
            k = os.path.relpath(k)
        print(f"[{mode}]\t'{k}' => '{bind}'")
    print("===================================================================")

    assert image is not None
    # Create and run the container
    container = client.containers.run(
        image,
        command=["sh", "run.sh"],
        working_dir="/workspace",
        environment=dict(env),
        detach=True,
        remove=True,
        auto_remove=True,
        # Type hint of docker is wrong here
        volumes=volumes,  # type: ignore
        network="host",  # Use the host network to avoid issues with localhost.
    )

    # Read the logs in a streaming fashion. Keep an eye on the time to make sure we don't need to stop.
    docker_timeout: float = timeout + 60  # One full minute after the bash timeout command should have already triggered
    start_time = time.time()
    logs = container.logs(stream=True)
    log_file = open(os.path.join(work_dir, "console_log.txt"), "wt", encoding="utf-8")
    stopping = False
    exiting = False

    while True:
        try:
            chunk = next(logs)  # Manually step the iterator so it is captures with the try-catch

            # Stream the data to the log file and the console
            chunk_str = chunk.decode("utf-8")
            log_file.write(chunk_str)
            log_file.flush()
            sys.stdout.reconfigure(encoding="utf-8")  # type: ignore
            sys.stdout.write(chunk_str)
            sys.stdout.flush()

            # Check if we need to terminate
            if not stopping and time.time() - start_time >= docker_timeout:
                container.stop()

                # Don't exit the loop right away, as there are things we may still want to read from the logs
                # but remember how we got here.
                stopping = True
        except KeyboardInterrupt:
            log_file.write("\nKeyboard interrupt (Ctrl-C). Attempting to exit gracefully.\n")
            log_file.flush()
            sys.stdout.write("\nKeyboard interrupt (Ctrl-C). Attempting to exit gracefully.\n")
            sys.stdout.flush()

            # Start the exit process, and give it a minute, but keep iterating
            container.stop()
            exiting = True
            docker_timeout = time.time() - start_time + 60
        except StopIteration:
            break

    # Clean up the container
    try:
        container.remove()
    except APIError:
        pass

    if stopping:  # By this line we've exited the loop, and the container has actually stopped.
        log_file.write("\nDocker timed out.\n")
        log_file.flush()
        sys.stdout.write("\nDocker timed out.\n")
        sys.stdout.flush()

    if exiting:  # User hit ctrl-C
        sys.exit(1)


def build_default_docker_image(docker_client: docker.DockerClient, image_tag: str) -> None:
    for segment in docker_client.api.build(
        path=RESOURCES_PATH,
        dockerfile="Dockerfile",
        rm=True,
        tag=image_tag,
        decode=True,
    ):
        if "stream" in segment:
            sys.stdout.write(segment["stream"])


def find_autogen_repo(path: str) -> Optional[str]:
    """
    Utility for identifying if the path is a subdirectory of the autogen_core repo.

    Returns: the path to the root of the autogen_core repo if one is found, otherwise None
    """

    # Normalize the path (we expect a directory)
    path = os.path.abspath(path)
    if os.path.isfile(path):
        path = os.path.dirname(path)

    while True:
        test_path = os.path.join(path, "python", "packages", "autogen-core")  # We found autogen_core
        if os.path.isdir(test_path):
            return path

        # Stop if we hit the root
        parent_dir = os.path.abspath(os.path.join(path, os.pardir))
        if parent_dir == path:
            break

        # Keep searching
        path = parent_dir

    return None


def split_jsonl(file_path: str, num_parts: int) -> List[List[Dict[str, Any]]]:
    """
    Split a JSONL file into num_parts approximately equal parts.
    """
    with open(file_path, "r") as f:
        data = [json.loads(line) for line in f]

    random.shuffle(data)  # Shuffle the data for better distribution
    chunk_size = len(data) // num_parts
    return [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]


def mkdir_p(path: str) -> None:
    """
    Create a directory if it doesn't exist, handling race conditions.
    """
    try:
        os.makedirs(path, exist_ok=True)
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise


def run_scenarios_subset(
    scenario_name: str,
    scenarios: List[Dict[str, Any]],
    n_repeats: int,
    is_native: bool,
    config_file: Union[None, str],
    docker_image: Optional[str] = None,
    results_dir: str = "Results",
    subsample: Union[None, int, float] = None,
    env_file: Union[None, str] = None,
) -> None:
    """
    Run a subset of agbench scenarios a given number of times.
    """
    for instance in scenarios:
        # Create a folder to store the results
        # Results base

        mkdir_p(results_dir)

        # Results for the scenario

        results_scenario = os.path.join(results_dir, scenario_name)
        mkdir_p(results_scenario)

        # Results for the instance
        results_instance = os.path.join(results_scenario, instance["id"])
        mkdir_p(results_instance)

        # Results for the repeats
        for i in range(0, n_repeats):
            results_repetition = os.path.join(results_instance, str(i))

            # Skip it if it already exists
            if os.path.isdir(results_repetition):
                print(f"Found folder {results_repetition} ... Skipping.")
                continue
            print(f"Running scenario {results_repetition}")

            # Expand the scenario
            expand_scenario(".", instance, results_repetition, config_file)  # type: ignore

            # Prepare the environment (keys/values that need to be added)
            env = get_scenario_env(env_file=env_file)

            # Run the scenario
            if is_native:
                run_scenario_natively(results_repetition, env)
            else:
                run_scenario_in_docker(
                    results_repetition,
                    env,
                    docker_image=docker_image,
                )


def run_parallel(args: argparse.Namespace) -> None:
    """
    Run scenarios in parallel.
    """
    # Read and split the JSONL file
    scenarios = split_jsonl(args.scenario, args.parallel)
    scenario_name_parts = os.path.basename(args.scenario).split(".")
    scenario_name_parts.pop()
    scenario_name = ".".join(scenario_name_parts)

    # Create a pool of worker processes
    with Pool(processes=args.parallel) as pool:
        # Prepare arguments for each worker
        worker_args = [
            (
                scenario_name,
                scenario_subset,
                args.repeat,
                args.native,
                args.config,
                args.docker_image,
                "Results",
                args.subsample,
                args.env,
            )
            for scenario_subset in scenarios
        ]

        # Run scenarios in parallel
        pool.starmap(run_scenarios_subset, worker_args)


def get_azure_token_provider() -> Optional[Callable[[], str]]:
    """
    Get the Azure bearer token generator if a token wasn't provided and there's any evidence of using Azure.
    """
    if not os.environ.get("AZURE_OPENAI_AD_TOKEN") and os.path.isdir(pathlib.Path("~/.azure").expanduser()):
        logging.disable(logging.CRITICAL)
        try:
            azure_token_provider = get_bearer_token_provider(
                DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
            )
            azure_token_provider()  # Call it once to warm it up, and make sure it doesn't throw an error
            print("Found Azure token provider.")
            return azure_token_provider
        except ClientAuthenticationError:
            error_message = traceback.format_exc()
            print(
                f"Azure token provider failed loading. Try using 'az login --use-device-code'\n\nError details:\n{error_message}\n\nContinuing without Azure token provider..."
            )
        logging.disable(logging.NOTSET)
    return None


def run_cli(args: Sequence[str]) -> None:
    invocation_cmd = args[0]
    args = args[1:]

    # Prepare the argument parser
    parser = argparse.ArgumentParser(
        prog=invocation_cmd,
        description=f"{invocation_cmd} will run the specified AutoGen scenarios for a given number of repetitions and record all logs and trace information. When running in a Docker environment (default), each run will begin from a common, tightly controlled, environment. The resultant logs can then be further processed by other scripts to produce metrics.".strip(),
    )

    parser.add_argument(
        "scenario",
        help="The JSONL scenario file to run. If a directory is specified, then all JSONL scenarios in the directory are run. If set to '-', then read from stdin.",
    )
    parser.add_argument(
        "-r",
        "--repeat",
        type=int,
        help="The number of repetitions to run for each scenario (default: 1).",
        default=1,
    )
    parser.add_argument(
        "-s",
        "--subsample",
        type=str,
        help='Run on a subsample of the tasks in the JSONL file(s). If a decimal value is specified, then run on the given proportion of tasks in each file. For example "0.7" would run on 70%% of tasks, and "1.0" would run on 100%% of tasks. If an integer value is specified, then randomly select *that* number of tasks from each specified JSONL file. For example "7" would run tasks, while "1" would run only 1 task from each specified JSONL file. (default: 1.0; which is 100%%)',
        default=None,
    )
    parser.add_argument(
        "-p",
        "--parallel",
        type=int,
        help="The number of parallel processes to run (default: 1).",
        default=1,
    )
    parser.add_argument(
        "-a",
        "--azure",
        action="store_true",
        help="Use Azure identity to pass an AZURE_OPENAI_AD_TOKEN to the task environment. This is necessary when using Azure-hosted OpenAI models rather than those hosted by OpenAI.",
    )
    parser.add_argument(
        "-e",
        "--env",
        type=str,
        help="The environment file to load into Docker, or into the native task context (default: '"
        + DEFAULT_ENV_FILE_YAML
        + "').",
        default=None,
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        help="The config file to copy into the Task (default: '" + DEFAULT_CONFIG_YAML + "').",
        default=None,
    )
    parser.add_argument(
        "-d",
        "--docker-image",
        type=str,
        help="The Docker image to use when running scenarios. Can not be used together with --native. (default: '"
        + DEFAULT_DOCKER_IMAGE_TAG
        + "', which will be created if not present)",
        default=None,
    )
    parser.add_argument(
        "--native",
        action="store_true",
        help="Run the scenarios natively rather than in docker. NOTE: This is not advisable, and should be done with great caution.",
    )

    parsed_args = parser.parse_args(args)

    if parsed_args.config is not None:
        # Make sure the config file is readable, so that we fail early
        with open(parsed_args.config, "r"):
            pass

    # don't support parallel and subsample together
    if parsed_args.parallel > 1 and parsed_args.subsample is not None:
        sys.exit("The options --parallel and --subsample can not be used together currently. Exiting.")

    # Don't allow both --docker-image and --native on the same command
    if parsed_args.docker_image is not None and parsed_args.native:
        sys.exit("The options --native and --docker-image can not be used together. Exiting.")

    # Warn if running natively
    if parsed_args.native:
        if IS_WIN32:
            sys.exit("Running scenarios with --native is not supported in Windows. Exiting.")

        sys.stderr.write(
            "WARNING: Running natively, without Docker, not only poses the usual risks of executing arbitrary AI generated code on your machine, it also makes it impossible to ensure that each test starts from a known and consistent set of initial conditions. For example, if the agents spend time debugging and installing Python libraries to solve the task, then those libraries will be available to all other runs. In other words, earlier runs can influence later runs, leading to many confounds in testing.\n\n"
        )

        # Does an environment variable override the prompt?
        allow_native = os.environ.get("AGBENCH_ALLOW_NATIVE")
        if allow_native is None or allow_native == "":
            choice = input(
                'Are you absolutely sure you want to continue with native execution? Type "Yes" exactly, and in full, to proceed: '
            )
            if choice.strip().lower() != "yes":
                sys.exit("Received '" + choice + "'. Exiting.")
        elif allow_native.strip().lower() != "yes":
            sys.exit(f"Exiting because AGBENCH_ALLOW_NATIVE is '{allow_native}'\n")
        else:
            sys.stderr.write(f"Continuing because AGBENCH_ALLOW_NATIVE is '{allow_native}'\n")
            time.sleep(0.75)  # Pause very briefly so the message isn't lost in the noise

    # Parse the subsample
    subsample = None
    if parsed_args.subsample is not None:
        subsample = float(parsed_args.subsample)
        if "." in parsed_args.subsample:  # Intention is to run on a proportion
            if subsample == 1.0:  # Intention is to run 100%, which is the default
                subsample = None  # None means 100% ... which use None to differentiate from the integer 1
            elif subsample < 0 or subsample > 1.0:
                raise (
                    ValueError(
                        "Subsample must either be an integer (specified without a decimal), or a Real number between 0.0 and 1.0"
                    )
                )

    # Get the Azure bearer token generator if a token wasn't provided and there's any evidence of using Azure
    azure_token_provider = None
    if parsed_args.azure:
        azure_token_provider = get_azure_token_provider()

    # Run the scenario
    if parsed_args.parallel > 1:
        run_parallel(parsed_args)
    else:
        run_scenarios(
            scenario=parsed_args.scenario,
            n_repeats=parsed_args.repeat,
            is_native=True if parsed_args.native else False,
            config_file=parsed_args.config,
            token_provider=azure_token_provider,
            docker_image=parsed_args.docker_image,
            subsample=subsample,
            env_file=parsed_args.env,
        )
