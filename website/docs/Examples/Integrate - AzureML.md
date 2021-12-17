FLAML can be used together with AzureML and mlflow.

### Prerequisites

Install the [azureml] option.
```bash
pip install "flaml[azureml]"
```

Setup a AzureML workspace:
```python
from azureml.core import Workspace

ws = Workspace.create(name='myworkspace', subscription_id='<azure-subscription-id>',resource_group='myresourcegroup')
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

# Download [Airlines dataset](https://www.openml.org/d/1169) from OpenML. The task is to predict whether a given flight will be delayed, given the information of the scheduled departure.
X_train, X_test, y_train, y_test = load_openml_dataset(dataset_id=1169, data_dir="./")

from flaml import AutoML

automl = AutoML()
settings = {
    "time_budget": 60,  # total running time in seconds
    "metric": "accuracy",  # metric to optimize
    "task": "classification",  # task type  
    "log_file_name": "airlines_experiment.log",  # flaml log file
}
mlflow.set_experiment("flaml")  # the experiment name in AzureML workspace
with mlflow.start_run() as run:  # create a mlflow run
    automl.fit(X_train=X_train, y_train=y_train, **settings)
```

The metrics in the run will be automatically logged in an experiment named "flaml" in your AzureML workspace.

[Link to notebook](https://github.com/microsoft/FLAML/blob/main/notebook/integrate_azureml.ipynb) | [Open in colab](https://colab.research.google.com/github/microsoft/FLAML/blob/main/notebook/integrate_azureml.ipynb)