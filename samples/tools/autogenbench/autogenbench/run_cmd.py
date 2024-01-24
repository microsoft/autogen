import os
import errno
import shutil
import subprocess
import json
import sys
import time
import pathlib
import argparse
import docker
import random
from autogen import config_list_from_json
from autogen.oai.openai_utils import filter_config

# Figure out where everything is
SCRIPT_PATH = os.path.realpath(__file__)
SCRIPT_NAME = os.path.basename(SCRIPT_PATH)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)

TASK_TIMEOUT = 60 * 30  # 30 minutes

BASE_TEMPLATE_PATH = os.path.join(SCRIPT_DIR, "template")
RESOURCES_PATH = os.path.join(SCRIPT_DIR, "res")

# What platform are we running?
IS_WIN32 = sys.platform == "win32"

# This is the tag given to the image that is *built* when no other image is provided.
# Do not use this field to specify the name of an existing image (e.g., on Dockerhub)
DEFAULT_DOCKER_IMAGE_TAG = "autogenbench:default"

DEFAULT_ENV_FILE = "ENV.json"


# Get a random number generator for subsampling
subsample_rng = random.Random(425)


def run_scenarios(
    scenario,
    n_repeats,
    is_native,
    config_list,
    requirements,
    docker_image=None,
    results_dir="Results",
    subsample=None,
):
    """
    Run a set autogenbench scenarios a given number of times.

    Args:
        scenario (path):    The file or folder containing the scenario JSONL instances. If given a folder, then
                            all JSONL files in the folder will be loaded and run.
        n_repeats (int):    The number of times each scenario instance will be repeated
        is_native (bool):   True if the scenario should be run locally rather than in Docker (proceed with caution!)
        config_list (list): An Autogen OAI_CONFIG_LIST to be used when running scenarios.
        results_dir (path): The folder were results will be saved.
    """

    files = []

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
        scenario_name = None
        scenario_dir = None
        file_handle = None

        # stdin
        if scenario_file == "-":
            scenario_name = "stdin"
            scenario_dir = "."
            file_handle = sys.stdin
        else:
            scenario_name = os.path.basename(scenario_file).split(".")
            scenario_name.pop()
            scenario_name = ".".join(scenario_name)
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
                expand_scenario(scenario_dir, instance, results_repetition, requirements)

                # Prepare the environment (keys/values that need to be added)
                env = get_scenario_env(config_list)

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


def expand_scenario(scenario_dir, scenario, output_dir, requirements):
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
        substitutions = {"scenario.py": substitutions}

    copy_operations = []

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

    # Copy the requirements file if specified
    if requirements is not None:
        shutil.copyfile(requirements, pathlib.Path(os.path.join(output_dir, "requirements.txt")))

    # Expand templated files
    for templated_file in substitutions.keys():  # Keys are relative file paths
        # Read the templated file into memory
        template_contents = list()
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


def get_scenario_env(config_list, env_file=DEFAULT_ENV_FILE):
    """
    Return a dictionary of environment variables needed to run a scenario.

    Args:
        config_list (list): An Autogen OAI_CONFIG_LIST to be used when running scenarios.
        env_file (str): The path to the env_file to read. (default: DEFAULT_ENV_FILE)

    Returns: A dictionary of keys and values that need to be added to the system environment.
    """
    env = dict()
    if os.path.isfile(env_file):
        with open(env_file, "rt") as fh:
            env = json.loads(fh.read())

    config_list_json = json.dumps(config_list)
    env["OAI_CONFIG_LIST"] = config_list_json

    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if openai_api_key is not None and len(openai_api_key.strip()) > 0:
        env["OPENAI_API_KEY"] = openai_api_key

    return env


def run_scenario_natively(work_dir, env, timeout=TASK_TIMEOUT):
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

# Run the global init script if it exists
if [ -f global_init.sh ] ; then
    . ./global_init.sh
fi

# Run the scenario init script if it exists
if [ -f scenario_init.sh ] ; then
    . ./scenario_init.sh
fi

# Run the scenario
echo SCENARIO.PY STARTING !#!#
timeout --preserve-status --kill-after {timeout  + 30}s {timeout}s python scenario.py
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo SCENARIO.PY EXITED WITH CODE: $EXIT_CODE !#!#
else
    echo SCENARIO.PY COMPLETE !#!#
fi

# Clean up
if [ -d .cache ] ; then
    rm -Rf .cache
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

    # Run the script and log the output
    with open("console_log.txt", "wb") as f:
        process = subprocess.Popen(
            ["sh", "run.sh"],
            env=full_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        for c in iter(lambda: process.stdout.read(1), b""):
            f.write(c)
            os.write(sys.stdout.fileno(), c)  # Write binary to stdout

    # Return where we started
    os.chdir(cwd)
    return


def run_scenario_in_docker(work_dir, env, timeout=TASK_TIMEOUT, docker_image=None):
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
        except docker.errors.ImageNotFound:
            print(f"Building default Docker image '{DEFAULT_DOCKER_IMAGE_TAG}'. This may take a few minutes...")
            try:
                build_default_docker_image(client, DEFAULT_DOCKER_IMAGE_TAG)
                image = client.images.get(DEFAULT_DOCKER_IMAGE_TAG)
            except docker.errors.DockerException:
                print(f"Failed to build image '{DEFAULT_DOCKER_IMAGE_TAG}'")

    # Otherwise get the requested image
    else:
        try:
            image = client.images.get(docker_image)
        except docker.errors.ImageNotFound:
            # pull the image
            print(f"Pulling image '{docker_image}'")
            try:
                image = client.images.pull(docker_image)
            except docker.errors.DockerException:
                print(f"Failed to pull image '{docker_image}'")

    # Prepare the run script
    with open(os.path.join(work_dir, "run.sh"), "wt", newline="\n") as f:
        f.write(
            f"""#
echo RUN.SH STARTING !#!#
export AUTOGEN_TESTBED_SETTING="Docker"
umask 000

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
timeout --preserve-status --kill-after {timeout  + 30}s {timeout}s python scenario.py
EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo SCENARIO.PY EXITED WITH CODE: $EXIT_CODE !#!#
else
    echo SCENARIO.PY COMPLETE !#!#
fi

# Clean up
if [ -d .cache ] ; then
    rm -Rf .cache
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

    print("\n\n" + work_dir + "\n===================================================================")

    # Create and run the container
    abs_path = str(pathlib.Path(work_dir).absolute())
    container = client.containers.run(
        image,
        command=["sh", "run.sh"],
        working_dir="/workspace",
        environment=env,
        detach=True,
        # get absolute path to the working directory
        volumes={abs_path: {"bind": "/workspace", "mode": "rw"}},
    )

    # Read the logs in a streaming fashion. Keep an eye on the time to make sure we don't need to stop.
    docker_timeout = timeout + 60  # One full minute after the bash timeout command should have already triggered
    start_time = time.time()
    logs = container.logs(stream=True)
    log_file = open(os.path.join(work_dir, "console_log.txt"), "wt")
    stopping = False

    for chunk in logs:  # When streaming it should return a generator
        # Stream the data to the log file and the console
        chunk = chunk.decode("utf-8")
        log_file.write(chunk)
        log_file.flush()
        sys.stdout.write(chunk)
        sys.stdout.flush()

        # Check if we need to terminate
        if not stopping and time.time() - start_time >= docker_timeout:
            container.stop()

            # Don't exit the loop right away, as there are things we may still want to read from the logs
            # but remember how we got here.
            stopping = True

    if stopping:  # By this line we've exited the loop, and the container has actually stopped.
        log_file.write("\nDocker timed out.\n")
        log_file.flush()
        sys.stdout.write("\nDocker timed out.\n")
        sys.stdout.flush()


def build_default_docker_image(docker_client, image_tag):
    for segment in docker_client.api.build(
        path=RESOURCES_PATH,
        dockerfile="Dockerfile",
        rm=True,
        tag=image_tag,
        decode=True,
    ):
        if "stream" in segment:
            sys.stdout.write(segment["stream"])


def run_cli(args):
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
        "-c",
        "--config",
        type=str,
        help="The environment variable name or path to the OAI_CONFIG_LIST (default: OAI_CONFIG_LIST).",
        default="OAI_CONFIG_LIST",
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
        "-m",
        "--model",
        type=str,
        help="Filters the config_list to include only models matching the provided model name or tag (default: None, which is all models).",
        default=None,
    )
    parser.add_argument(
        "--requirements",
        type=str,
        help="The requirements file to pip install before running the scenario.",
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

    # Load the OAI_CONFIG_LIST
    config_list = config_list_from_json(env_or_file=parsed_args.config)

    # Add the model name to the tags to simplify filtering
    for entry in config_list:
        if "tags" not in entry:
            entry["tags"] = list()
        if entry["model"] not in entry["tags"]:
            entry["tags"].append(entry["model"])

    # Filter if requested
    if parsed_args.model is not None:
        filter_dict = {"tags": [parsed_args.model]}
        config_list = filter_config(config_list, filter_dict)
        if len(config_list) == 0:
            sys.exit(
                f"The model configuration list is empty. This may be because the model filter '{parsed_args.model}' returned 0 results."
            )

    # Don't allow both --docker-image and --native on the same command
    if parsed_args.docker_image is not None and parsed_args.native:
        sys.exit("The options --native and --docker-image can not be used together. Exiting.")

    # Warn if running natively
    if parsed_args.native:
        if IS_WIN32:
            sys.exit("Running scenarios with --native is not supported in Windows. Exiting.")

        if parsed_args.requirements is not None:
            sys.exit("--requirements is not compatible with --native. Exiting.")

        choice = input(
            'WARNING: Running natively, without Docker, not only poses the usual risks of executing arbitrary AI generated code on your machine, it also makes it impossible to ensure that each test starts from a known and consistent set of initial conditions. For example, if the agents spend time debugging and installing Python libraries to solve the task, then those libraries will be available to all other runs. In other words, earlier runs can influence later runs, leading to many confounds in testing.\n\nAre you absolutely sure you want to continue with native execution? Type "Yes" exactly, and in full, to proceed: '
        )

        if choice.strip().lower() != "yes":
            sys.exit("Received '" + choice + "'. Exiting.")

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

    run_scenarios(
        scenario=parsed_args.scenario,
        n_repeats=parsed_args.repeat,
        is_native=True if parsed_args.native else False,
        config_list=config_list,
        requirements=parsed_args.requirements,
        docker_image=parsed_args.docker_image,
        subsample=subsample,
    )
