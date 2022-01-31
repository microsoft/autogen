import time
from azureml.core import Workspace, Experiment, ScriptRunConfig, Environment

ws = Workspace.from_config()
ray_environment_name = "aml-ray-cpu"
ray_environment_dockerfile_path = "./Docker/Dockerfile-cpu"

# Build CPU image for Ray
ray_cpu_env = Environment.from_dockerfile(
    name=ray_environment_name, dockerfile=ray_environment_dockerfile_path
)
ray_cpu_env.register(workspace=ws)
ray_cpu_build_details = ray_cpu_env.build(workspace=ws)

while ray_cpu_build_details.status not in ["Succeeded", "Failed"]:
    print(
        f"Awaiting completion of ray CPU environment build. Current status is: {ray_cpu_build_details.status}"
    )
    time.sleep(10)

env = Environment.get(workspace=ws, name=ray_environment_name)
compute_target = ws.compute_targets["cpucluster"]
command = ["python distribute_tune.py"]
config = ScriptRunConfig(
    source_directory="ray/",
    command=command,
    compute_target=compute_target,
    environment=env,
)
config.run_config.node_count = 2
config.run_config.environment_variables["_AZUREML_CR_START_RAY"] = "true"
config.run_config.environment_variables["AZUREML_COMPUTE_USE_COMMON_RUNTIME"] = "true"

exp = Experiment(ws, "test-ray")
run = exp.submit(config)
print(run.get_portal_url())  # link to ml.azure.com
run.wait_for_completion(show_output=True)
