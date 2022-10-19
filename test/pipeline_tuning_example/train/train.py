import argparse
import lightgbm as lgb
import os
import pandas as pd
from azureml.core import Run


class LightGBMCallbackHandler:
    def __init__(self):
        pass

    def callback(self, env: lgb.callback.CallbackEnv) -> None:
        """Callback method to collect metrics produced by LightGBM.

        See https://lightgbm.readthedocs.io/en/latest/_modules/lightgbm/callback.html
        """
        # loop on all the evaluation results tuples
        print("env.evaluation_result_list:", env.evaluation_result_list)
        for data_name, eval_name, result, _ in env.evaluation_result_list:
            run = Run.get_context()
            run.log(f"{data_name}_{eval_name}", result)


def main(args):
    """Main function of the script."""

    train_path = os.path.join(args.train_data, "data.csv")
    print("traning_path:", train_path)

    test_path = os.path.join(args.test_data, "data.csv")

    train_set = lgb.Dataset(train_path)
    test_set = lgb.Dataset(test_path)
    callbacks_handler = LightGBMCallbackHandler()
    config = {
        "header": True,
        "objective": "binary",
        "label_column": 30,
        "metric": "binary_error",
        "n_estimators": args.n_estimators,
        "learning_rate": args.learning_rate,
    }
    gbm = lgb.train(
        config,
        train_set,
        valid_sets=[test_set],
        valid_names=["eval"],
        callbacks=[
            callbacks_handler.callback,
        ],
    )

    print("Saving model...")
    # save model to file
    gbm.save_model(os.path.join(args.model, "model.txt"))


if __name__ == "__main__":
    # input and output arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--train_data", type=str, help="path to train data")
    parser.add_argument("--test_data", type=str, help="path to test data")
    parser.add_argument("--n_estimators", required=False, default=100, type=int)
    parser.add_argument("--learning_rate", required=False, default=0.1, type=float)
    parser.add_argument("--model", type=str, help="path to output directory")
    args = parser.parse_args()
    main(args)
