import os
import errno
import shutil
import subprocess
import json
import sys
import time
import pathlib
import argparse

# Location of the environment directory
ENV_DIR = "./includes"


def run_scenarios(scenario, n_repeats, is_native, results_dir="results"):
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

                scenario_name + "_" + instance["id"]

                # Create a folder to store the results

                # Results base
                if not os.path.isdir(results_dir):
                    os.mkdir(results_dir)

                # Results for the scenario
                results_scenario = os.path.join(results_dir, scenario_name)
                if not os.path.isdir(results_scenario):
                    os.mkdir(results_scenario)

                # Results fot the instance
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

                    # Create the folder, and copy the script to a standard name
                    os.mkdir(results_repetition)
                    expand_scenario(scenario_dir, instance, os.path.join(results_repetition, "scenario.py"))

                    # Also copy the contents of ENV_DIR
                    for item in os.listdir(ENV_DIR):
                        if item.endswith(".example"):
                            continue
                        item_path = os.path.join(ENV_DIR, item)
                        if os.path.isfile(item_path):
                            shutil.copyfile(item_path, os.path.join(results_repetition, item))

                    # Run the scenario
                    if is_native:
                        run_scenario_natively(results_repetition)
                    else:
                        run_scenario_in_docker(results_repetition)


def expand_scenario(scenario_dir, scenario, output_file):
    template_fh = open(os.path.join(scenario_dir, scenario["template"]), "rt")
    output_fh = open(output_file, "wt")

    for line in template_fh:
        if "values" in scenario:
            for k, v in scenario["values"].items():
                line = line.replace(k, v)
        output_fh.write(line)

    template_fh.close()
    output_fh.close()


def run_scenario_natively(work_dir):
    # Get the current working directory
    cwd = os.getcwd()

    # Navigate to the scenario
    os.chdir(work_dir)
    print("\n\n" + os.getcwd() + "\n===================================================================")

    # Prepare the run script
    with open(os.path.join("run.sh"), "wt") as f:
        f.write(
            """#
. ./ENV
python scenario.py
rm ENV
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


def run_scenario_in_docker(work_dir, timeout=600):
    # Create a docker client
    client = docker.from_env()
    image_name = "python:3.11"

    # Pull a suitable image
    try:
        image = client.images.get(image_name)
    except docker.errors.ImageNotFound:
        # pull the image
        print("Pulling image", image_name)
        try:
            image = client.images.pull(image_name)
        except docker.errors.DockerException:
            print("Failed to pull image", image_name)

    # Prepare the run script
    with open(os.path.join(work_dir, "run.sh"), "wt") as f:
        f.write(
            """#
. ./ENV
pip install pyautogen
python scenario.py
rm ENV
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

        logs = container.logs().decode("utf-8").rstrip() + "\nDocker timed out."
        print(logs)
        with open(os.path.join(work_dir, "console_log.txt"), "wt") as f:
            f.write(logs)

        container.remove()
        return

    # get the container logs
    logs = container.logs().decode("utf-8").rstrip()
    container.remove()

    print(logs)
    with open(os.path.join(work_dir, "console_log.txt"), "wt") as f:
        f.write(logs)


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
        "-r", "--repeat", type=int, help="The number of repetitions to run for each scenario (default: 10).", default=10
    )
    parser.add_argument(
        "--native",
        action="store_true",
        help="Run the scenarios natively rather than in docker. NOTE: This is not advisable, and should be done with great caution.",
    )

    args = parser.parse_args()

    if args.native:
        choice = input(
            'WARNING: Running natively, without Docker, not only poses the usual risks of executing arbitrary AI generated code on your machine, it also makes it impossible to ensure that each test starts from a known and consistent set of initial conditions. For example, if the agents spend time debugging and installing Python libraries to solve the task, then those libraries will be available to all other runs. In other words, earlier runs can influence later runs, leading to many confounds in testing.\n\nAre you absolutely sure you want to continue with native execution? Type "Yes" exactly, and in full, to proceed: '
        )

        if choice.strip().lower() != "yes":
            print("Received '" + choice + "'. Exiting.")

    # Import docker if needed
    is_native = True if args.native else False
    if not is_native:
        import docker

    # Warn aboit a common error
    env_file = os.path.join(ENV_DIR, "ENV")
    example_file = os.path.join(ENV_DIR, "ENV.example")
    if not os.path.isfile(env_file):
        sys.exit(
            f"The environment file '{env_file}' does not exist. If this is your first time setting up the testbed, you will want to rename '{example_file}' to '{env_file}' and edit it to include your API keys and configurations."
        )

    run_scenarios(args.scenario, args.repeat, is_native)
