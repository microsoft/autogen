import logging
from azureml.core import Workspace
from azure.ml.component import (
    Component,
    dsl,
)
import argparse
from pathlib import Path

LOCAL_DIR = Path(__file__).parent.absolute()


def remote_run():
    ################################################
    # connect to your Azure ML workspace
    ################################################
    ws = Workspace(
        subscription_id=args.subscription_id,
        resource_group=args.resource_group,
        workspace_name=args.workspace,
    )

    ################################################
    # load component functions
    ################################################

    pipeline_tuning_func = Component.from_yaml(ws, yaml_file=LOCAL_DIR / "tuner/component_spec.yaml")

    ################################################
    # build pipeline
    ################################################
    @dsl.pipeline(
        name="pipeline_tuning",
        default_compute_target="cpucluster",
    )
    def sample_pipeline():
        pipeline_tuning_func()

    pipeline = sample_pipeline()

    run = pipeline.submit(regenerate_outputs=False)
    return run


def local_run():
    logger.info("Run tuner locally.")
    from tuner import tuner_func

    tuner_func.tune_pipeline(concurrent_run=2)


if __name__ == "__main__":
    # parser argument
    parser = argparse.ArgumentParser()
    parser.add_mutually_exclusive_group(required=False)
    parser.add_argument(
        "--subscription_id",
        type=str,
        help="your_subscription_id",
        required=False,
    )
    parser.add_argument("--resource_group", type=str, help="your_resource_group", required=False)
    parser.add_argument("--workspace", type=str, help="your_workspace", required=False)

    parser.add_argument("--remote", dest="remote", action="store_true")
    parser.add_argument("--local", dest="remote", action="store_false")
    parser.set_defaults(remote=True)
    args = parser.parse_args()

    logger = logging.getLogger(__name__)

    if args.remote:
        remote_run()
    else:
        local_run()
