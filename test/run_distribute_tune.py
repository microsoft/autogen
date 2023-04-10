import time
from azureml.core import Workspace, Experiment, ScriptRunConfig, Environment
from azureml.core.runconfig import RunConfiguration, DockerConfiguration

ws = Workspace.from_config()
ray_environment_name = "aml-ray-cpu"
ray_environment_dockerfile_path = "./Docker/Dockerfile-cpu"

# Build CPU image for Ray
ray_cpu_env = Environment.from_dockerfile(name=ray_environment_name, dockerfile=ray_environment_dockerfile_path)
ray_cpu_env.register(workspace=ws)
ray_cpu_build_details = ray_cpu_env.build(workspace=ws)

while ray_cpu_build_details.status not in ["Succeeded", "Failed"]:
    print(f"Awaiting completion of ray CPU environment build. Current status is: {ray_cpu_build_details.status}")
    time.sleep(10)

command = ["python distribute_tune.py"]
env = Environment.get(workspace=ws, name=ray_environment_name)
compute_target = ws.compute_targets["cpucluster"]
aml_run_config = RunConfiguration(communicator="OpenMpi")
aml_run_config.target = compute_target
aml_run_config.docker = DockerConfiguration(use_docker=True)
aml_run_config.environment = env
aml_run_config.node_count = 2
config = ScriptRunConfig(
    source_directory="ray/",
    command=command,
    run_config=aml_run_config,
)

exp = Experiment(ws, "distribute-tune")
run = exp.submit(config)
print(run.get_portal_url())  # link to ml.azure.com
run.wait_for_completion(show_output=True)
