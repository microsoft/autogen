from dataclasses import dataclass
from pathlib import Path
import azureml.core
from azureml.core import Workspace, Dataset, Run
from azure.ml.component import (
    Component,
    dsl,
)
import hydra
from hydra.core.config_store import ConfigStore
from hydra.utils import to_absolute_path


@dataclass
class AMLConfig:
    subscription_id: str
    resource_group: str
    workspace: str


@dataclass
class TrainConfig:
    exp_name: str
    data_path: str
    test_train_ratio: float
    learning_rate: float
    n_estimators: int


@dataclass
class PipelineConfig:
    aml_config: AMLConfig
    train_config: TrainConfig


LOCAL_DIR = Path(__file__).parent.absolute()
TARGET_DATA_DIR = "classification_data"

cs = ConfigStore.instance()
cs.store(name="config", node=PipelineConfig)


@hydra.main(config_path="configs", config_name="train_config")
def main(config: PipelineConfig):
    build_and_submit_aml_pipeline(config)


def build_and_submit_aml_pipeline(config):
    """This function can be called from Python
    while the main function is meant for CLI only.
    When calling the main function in Python,
    there is error due to the hydra.main decorator
    """

    if isinstance(config, list):
        with hydra.initialize(config_path="configs"):
            config = hydra.compose(config_name="train_config", overrides=config)

    ################################################
    # connect to your Azure ML workspace
    ################################################
    if isinstance(Run.get_context(), azureml.core.run._OfflineRun):
        ws = Workspace(
            subscription_id=config.aml_config.subscription_id,
            resource_group=config.aml_config.resource_group,
            workspace_name=config.aml_config.workspace_name,
        )
    else:
        ws = Run.get_context().experiment.workspace

    ################################################
    # load input datasets:
    ################################################
    datastore = ws.get_default_datastore()
    Dataset.File.upload_directory(
        src_dir=to_absolute_path(LOCAL_DIR / "data"),
        target=(datastore, TARGET_DATA_DIR),
        overwrite=True,
    )

    dataset = Dataset.File.from_files(path=(datastore, TARGET_DATA_DIR))

    ################################################
    # load component functions
    ################################################
    data_prep_component = Component.from_yaml(
        ws, yaml_file=LOCAL_DIR / "data_prep/data_prep.yaml"
    )
    train_component = Component.from_yaml(ws, yaml_file=LOCAL_DIR / "train/train.yaml")

    ################################################
    # build pipeline
    ################################################
    # TODO: update the pipeline
    @dsl.pipeline(
        default_compute_target="cpucluster",
    )
    def train_pipeline():
        data_prep_job = data_prep_component(
            data=dataset,
            test_train_ratio=config.train_config.test_train_ratio,
        )

        train_component(
            train_data=data_prep_job.outputs.train_data,
            test_data=data_prep_job.outputs.test_data,
            learning_rate=config.train_config.learning_rate,
            n_estimators=config.train_config.n_estimators,
        )

        return

    pipeline = train_pipeline()

    tags = {
        "n_estimators": str(config.train_config.n_estimators),
        "learning_rate": str(config.train_config.learning_rate),
    }

    # submit the pipeline
    run = pipeline.submit(tags=tags, regenerate_outputs=False)

    return run


if __name__ == "__main__":
    main()
