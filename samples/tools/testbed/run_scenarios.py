import os
import errno
import shutil
import subprocess
import json
import sys
import time
import pathlib
import argparse
from autogen import config_list_from_json

# What platform are we running?
IS_WIN32 = sys.platform == "win32"

# Location of the global includes dir. The contents of this directory will be copied to the Docker environment.
GLOBAL_INCLUDES_DIR = "includes"

# This is the tag given to the image that is *built* when no other image is provided.
# Do not use this field to specify the name of an existing image (e.g., on Dockerhub)
DEFAULT_DOCKER_IMAGE_TAG = "autogen/testbed:default"


def run_scenarios(scenario, n_repeats, is_native, config_list, requirements, docker_image=None, results_dir="results"):
    """
    Run a set testbed scenarios a given number of times.

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
    if os.path.isfile(scenario):
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
        scenario_name = os.path.basename(scenario_file).split(".")
        scenario_name.pop()
        scenario_name = ".".join(scenario_name)

        scenario_dir = os.path.dirname(os.path.realpath(scenario_file))

        # Each line in the scenario file is an instance. Run it.
        with open(scenario_file) as fh:
            for line in fh:
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
                    expand_scenario(scenario_dir, instance, results_repetition)

                    # Append the config list to the ENV file
                    with open(os.path.join(results_repetition, "ENV"), "at") as fh:
                        config_list_json = json.dumps(config_list)
                        fh.write(f"export OAI_CONFIG_LIST='{config_list_json}'\n")

                        # If set, append the OpenAI API Key
                        openai_api_key = os.environ.get("OPENAI_API_KEY")
                        if openai_api_key is not None and len(openai_api_key.strip()) > 0:
                            fh.write(f"export OPENAI_API_KEY='{openai_api_key}'\n")

                    # Run the scenario
                    if is_native:
                        run_scenario_natively(results_repetition)
                    else:
                        run_scenario_in_docker(results_repetition, requirements, docker_image=docker_image)


def expand_scenario(scenario_dir, scenario, output_dir):
    """
    Expand a scenario into a folder.
    Despite some awkwardness created by backwards compatibility and notational conveniences, expansion is conceptually simple.
    It is a series of copy commands (similar to `cp -R`), followed by a series of in-place fine and replace operations.
    """

    template = scenario["template"]

    # Either key works for finding the substitutions list. "values" may be deprecated in the future
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
    shutil.copytree(GLOBAL_INCLUDES_DIR, output_dir, ignore=shutil.ignore_patterns("*.example"), dirs_exist_ok=False)

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
                # Otherwise use the filename provided
                shutil.copyfile(src_path, dest_path)

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


def run_scenario_natively(work_dir):
    """
    Run a scenario in the native environment.

    Args:
        work_dir (path): the path to the working directory previously created to house this scenario instance
    """

    # Get the current working directory
    cwd = os.getcwd()

    # Navigate to the scenario
    os.chdir(work_dir)
    print("\n\n" + os.getcwd() + "\n===================================================================")

    # Prepare the run script
    with open(os.path.join("run.sh"), "wt") as f:
        f.write(
            """#
export AUTOGEN_TESTBED_SETTING="Native"

# Read the environment variables
. ./ENV

# Run the global init script if it exists
if [ -f global_init.sh ] ; then
    . ./global_init.sh
fi

# Run the scenario init script if it exists
if [ -f scenario_init.sh ] ; then
    . ./scenario_init.sh
fi

# Run the scenario
python scenario.py

# Clean up
rm ENV
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

echo SCENARIO COMPLETE !#!#
"""
        )

    # Run the script and log the output
    with open("console_log.txt", "wb") as f:
        process = subprocess.Popen(["sh", "run.sh"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        for c in iter(lambda: process.stdout.read(1), b""):
            f.write(c)
            os.write(sys.stdout.fileno(), c)  # Write binary to stdout

    # Return where we started
    os.chdir(cwd)
    return


def run_scenario_in_docker(work_dir, requirements, timeout=600, docker_image=None):
    """
    Run a scenario in a Docker environment.

    Args:
        work_dir (path): the path to the working directory previously created to house this scenario instance
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
export AUTOGEN_TESTBED_SETTING="Docker"
umask 000

# Read the environment variables
. ./ENV

# Run the global init script if it exists
if [ -f global_init.sh ] ; then
    . ./global_init.sh
fi

# Run the scenario init script if it exists
if [ -f scenario_init.sh ] ; then
    . ./scenario_init.sh
fi

# Run the scenario
pip install -r {requirements}
python scenario.py

# Clean up
rm ENV
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

echo SCENARIO COMPLETE !#!#
"""
        )

    print("\n\n" + work_dir + "\n===================================================================")

    # Create and run the container
    abs_path = str(pathlib.Path(work_dir).absolute())
    container = client.containers.run(
        image,
        command=["sh", "run.sh"],
        working_dir="/workspace",
        detach=True,
        # get absolute path to the working directory
        volumes={abs_path: {"bind": "/workspace", "mode": "rw"}},
    )

    # Poll until the container is done, or we've timed out
    start_time = time.time()
    while container.status != "exited" and time.time() - start_time < timeout:
        # Reload the container object
        container.reload()

    if container.status != "exited":
        container.stop()

        logs = container.logs().decode("utf-8").rstrip() + "\nDocker timed out.\n"
        print(logs)
        with open(os.path.join(work_dir, "console_log.txt"), "wt") as f:
            f.write(logs)

        container.remove()
        return

    # get the container logs
    logs = container.logs().decode("utf-8").rstrip() + "\n"
    container.remove()

    print(logs)
    with open(os.path.join(work_dir, "console_log.txt"), "wt") as f:
        f.write(logs)


def build_default_docker_image(docker_client, image_tag):
    for segment in docker_client.api.build(path=".", dockerfile="Dockerfile", rm=True, tag=image_tag, decode=True):
        if "stream" in segment:
            sys.stdout.write(segment["stream"])


###############################################################################
if __name__ == "__main__":
    script_name = os.path.basename(__file__)
    parser = argparse.ArgumentParser(
        description=f"{script_name} will run the specified autogen scenarios for a given number of repetitions and record all logs and trace information. When running in a Docker environment (default), each run will begin from a common, tightly controlled, environment. The resultant logs can then be further processed by other scripts to produce metrics.".strip()
    )

    parser.add_argument(
        "scenario",
        nargs="?",
        help="The JSONL scenario file to run. If a directory is specified, then all JSONL scenarios in the directory are run. (default: ./scenarios)",
        default="scenarios",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        help="The environment variable name or path to the OAI_CONFIG_LIST (default: OAI_CONFIG_LIST).",
        default="OAI_CONFIG_LIST",
    )
    parser.add_argument(
        "-r", "--repeat", type=int, help="The number of repetitions to run for each scenario (default: 1).", default=1
    )
    parser.add_argument(
        "--requirements",
        type=str,
        help="The requirements file to pip install before running the scenario. This file must be found in the '"
        + GLOBAL_INCLUDES_DIR
        + "' directory. (default: requirements.txt)",
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

    args = parser.parse_args()

    # Load the OAI_CONFIG_LIST
    config_list = config_list_from_json(env_or_file=args.config)
    if len(config_list) == 0:
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), args.config)

    # Don't allow both --docker-image and --native on the same command
    if args.docker_image is not None and args.native:
        sys.exit("The options --native and --docker-image can not be used together. Exiting.")

    # Warn if running natively
    if args.native:
        if IS_WIN32:
            sys.exit("Running scenarios with --native is not supported in Windows. Exiting.")

        if args.requirements is not None:
            sys.exit("--requirements is not compatible with --native. Exiting.")

        choice = input(
            'WARNING: Running natively, without Docker, not only poses the usual risks of executing arbitrary AI generated code on your machine, it also makes it impossible to ensure that each test starts from a known and consistent set of initial conditions. For example, if the agents spend time debugging and installing Python libraries to solve the task, then those libraries will be available to all other runs. In other words, earlier runs can influence later runs, leading to many confounds in testing.\n\nAre you absolutely sure you want to continue with native execution? Type "Yes" exactly, and in full, to proceed: '
        )

        if choice.strip().lower() != "yes":
            sys.exit("Received '" + choice + "'. Exiting.")

    # What requirements file are we working with?
    requirements = "requirements.txt"
    if args.requirements is not None:
        requirements = args.requirements

    is_native = True if args.native else False
    if not is_native:
        # Import docker
        import docker

        # Make sure the requirements file exists
        req_file = os.path.join(GLOBAL_INCLUDES_DIR, requirements)
        if not os.path.isfile(req_file):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), req_file)

    # Warn about a common error
    env_file = os.path.join(GLOBAL_INCLUDES_DIR, "ENV")
    example_file = os.path.join(GLOBAL_INCLUDES_DIR, "ENV.example")
    if not os.path.isfile(env_file):
        shutil.copyfile(example_file, env_file)
        sys.stderr.write(
            f"The environment file '{env_file}' does not exist (perhaps this is your first time setting up the testbed). A default environment file has been provided, but you may want to edit it to include your API keys and configurations.\n"
        )

    run_scenarios(args.scenario, args.repeat, is_native, config_list, requirements, docker_image=args.docker_image)
