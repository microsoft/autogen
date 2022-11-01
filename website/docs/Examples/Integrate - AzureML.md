FLAML can be used together with AzureML. On top of that, using mlflow and ray is easy too.

### Prerequisites

Install the [azureml] option.
```bash
pip install "flaml[azureml]"
```

Setup a AzureML workspace:
```python
from azureml.core import Workspace

ws = Workspace.create(name='myworkspace', subscription_id='<azure-subscription-id>', resource_group='myresourcegroup')
```

### Enable mlflow in AzureML workspace

```python
import mlflow
from azureml.core import Workspace

ws = Workspace.from_config()
mlflow.set_tracking_uri(ws.get_mlflow_tracking_uri())
```

### Start an AutoML run

```python
from flaml.data import load_openml_dataset
from flaml import AutoML

# Download [Airlines dataset](https://www.openml.org/d/1169) from OpenML. The task is to predict whether a given flight will be delayed, given the information of the scheduled departure.
X_train, X_test, y_train, y_test = load_openml_dataset(dataset_id=1169, data_dir="./")

automl = AutoML()
settings = {
    "time_budget": 60,  # total running time in seconds
    "metric": "accuracy",  # metric to optimize
    "task": "classification",  # task type
    "log_file_name": "airlines_experiment.log",  # flaml log file
}
experiment = mlflow.set_experiment("flaml")  # the experiment name in AzureML workspace
with mlflow.start_run() as run:  # create a mlflow run
    automl.fit(X_train=X_train, y_train=y_train, **settings)
    mlflow.sklearn.log_model(automl, "automl")
```

The metrics in the run will be automatically logged in an experiment named "flaml" in your AzureML workspace. They can be retrieved by `mlflow.search_runs`:

```python
mlflow.search_runs(experiment_ids=[experiment.experiment_id], filter_string="params.learner = 'xgboost'")
```

The logged model can be loaded and used to make predictions:
```python
automl = mlflow.sklearn.load_model(f"{run.info.artifact_uri}/automl")
print(automl.predict(X_test))
```

[Link to notebook](https://github.com/microsoft/FLAML/blob/main/notebook/integrate_azureml.ipynb) | [Open in colab](https://colab.research.google.com/github/microsoft/FLAML/blob/main/notebook/integrate_azureml.ipynb)

### Use ray to distribute across a cluster

When you have a compute cluster in AzureML, you can distribute `flaml.AutoML` or `flaml.tune` with ray.

#### Build a ray environment in AzureML

Create a docker file such as [.Docker/Dockerfile-cpu](https://github.com/microsoft/FLAML/blob/main/test/.Docker/Dockerfile-cpu). Make sure `RUN pip install flaml[blendsearch,ray]` is included in the docker file.

Then build a AzureML environment in the workspace `ws`.

```python
ray_environment_name = "aml-ray-cpu"
ray_environment_dockerfile_path = "./Docker/Dockerfile-cpu"

# Build CPU image for Ray
ray_cpu_env = Environment.from_dockerfile(name=ray_environment_name, dockerfile=ray_environment_dockerfile_path)
ray_cpu_env.register(workspace=ws)
ray_cpu_build_details = ray_cpu_env.build(workspace=ws)

import time
while ray_cpu_build_details.status not in ["Succeeded", "Failed"]:
    print(f"Awaiting completion of ray CPU environment build. Current status is: {ray_cpu_build_details.status}")
    time.sleep(10)
```

You only need to do this step once for one workspace.

#### Create a compute cluster with multiple nodes

```python
from azureml.core.compute import AmlCompute, ComputeTarget

compute_target_name = "cpucluster"
node_count = 2

# This example uses CPU VM. For using GPU VM, set SKU to STANDARD_NC6
compute_target_size = "STANDARD_D2_V2"

if compute_target_name in ws.compute_targets:
    compute_target = ws.compute_targets[compute_target_name]
    if compute_target and type(compute_target) is AmlCompute:
        if compute_target.provisioning_state == "Succeeded":
            print("Found compute target; using it:", compute_target_name)
        else:
            raise Exception(
                "Found compute target but it is in state", compute_target.provisioning_state)
else:
    print("creating a new compute target...")
    provisioning_config = AmlCompute.provisioning_configuration(
        vm_size=compute_target_size,
        min_nodes=0,
        max_nodes=node_count)

    # Create the cluster
    compute_target = ComputeTarget.create(ws, compute_target_name, provisioning_config)

    # Can poll for a minimum number of nodes and for a specific timeout.
    # If no min node count is provided it will use the scale settings for the cluster
    compute_target.wait_for_completion(show_output=True, min_node_count=None, timeout_in_minutes=20)

    # For a more detailed view of current AmlCompute status, use get_status()
    print(compute_target.get_status().serialize())
```

If the computer target "cpucluster" already exists, it will not be recreated.

#### Run distributed AutoML job

Assuming you have an automl script like [ray/distribute_automl.py](https://github.com/microsoft/FLAML/blob/main/test/ray/distribute_automl.py). It uses `n_concurrent_trials=k` to inform `AutoML.fit()` to perform k concurrent trials in parallel.

Submit an AzureML job as the following:

```python
from azureml.core import Workspace, Experiment, ScriptRunConfig, Environment
from azureml.core.runconfig import RunConfiguration, DockerConfiguration

command = ["python distribute_automl.py"]
ray_environment_name = "aml-ray-cpu"
env = Environment.get(workspace=ws, name=ray_environment_name)
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

exp = Experiment(ws, "distribute-automl")
run = exp.submit(config)

print(run.get_portal_url())  # link to ml.azure.com
run.wait_for_completion(show_output=True)
```

#### Run distributed tune job

Prepare a script like [ray/distribute_tune.py](https://github.com/microsoft/FLAML/blob/main/test/ray/distribute_tune.py). Replace the command in the above eample with:

```python
command = ["python distribute_tune.py"]
```

Everything else is the same.
