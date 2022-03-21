import sys
import pytest


def custom_metric(
    X_test,
    y_test,
    estimator,
    labels,
    X_train,
    y_train,
    weight_test=None,
    weight_train=None,
    config=None,
    groups_test=None,
    groups_train=None,
):
    from datasets import Dataset
    from flaml.model import TransformersEstimator

    if estimator._trainer is None:
        trainer, _, _ = estimator._init_model_for_predict(X_test)
        estimator._trainer = None
    else:
        trainer = estimator._trainer
    if y_test is not None:
        X_test, _ = estimator._preprocess(X_test)
        eval_dataset = Dataset.from_pandas(TransformersEstimator._join(X_test, y_test))
    else:
        X_test, _ = estimator._preprocess(X_test)
        eval_dataset = Dataset.from_pandas(X_test)

    estimator_metric_backup = estimator._metric
    estimator._metric = "rmse"
    metrics = trainer.evaluate(eval_dataset)
    estimator._metric = estimator_metric_backup

    return metrics.pop("eval_automl_metric"), metrics


@pytest.mark.skipif(sys.platform == "darwin", reason="do not run on mac os")
def test_custom_metric():
    from flaml import AutoML
    import pandas as pd
    import requests

    train_data = {
        "sentence1": [
            'Amrozi accused his brother , whom he called " the witness " , of deliberately distorting his evidence .',
            "Yucaipa owned Dominick 's before selling the chain to Safeway in 1998 for $ 2.5 billion .",
            "They had published an advertisement on the Internet on June 10 , offering the cargo for sale , he added .",
            "Around 0335 GMT , Tab shares were up 19 cents , or 4.4 % , at A $ 4.56 , having earlier set a record high of A $ 4.57 .",
        ],
        "sentence2": [
            'Referring to him as only " the witness " , Amrozi accused his brother of deliberately distorting his evidence .',
            "Yucaipa bought Dominick 's in 1995 for $ 693 million and sold it to Safeway for $ 1.8 billion in 1998 .",
            "On June 10 , the ship 's owners had published an advertisement on the Internet , offering the explosives for sale .",
            "Tab shares jumped 20 cents , or 4.6 % , to set a record closing high at A $ 4.57 .",
        ],
        "label": [1, 0, 1, 0],
        "idx": [0, 1, 2, 3],
    }
    train_dataset = pd.DataFrame(train_data)

    dev_data = {
        "sentence1": [
            "The stock rose $ 2.11 , or about 11 percent , to close Friday at $ 21.51 on the New York Stock Exchange .",
            "Revenue in the first quarter of the year dropped 15 percent from the same period a year earlier .",
            "The Nasdaq had a weekly gain of 17.27 , or 1.2 percent , closing at 1,520.15 on Friday .",
            "The DVD-CCA then appealed to the state Supreme Court .",
        ],
        "sentence2": [
            "PG & E Corp. shares jumped $ 1.63 or 8 percent to $ 21.03 on the New York Stock Exchange on Friday .",
            "With the scandal hanging over Stewart 's company , revenue the first quarter of the year dropped 15 percent from the same period a year earlier .",
            "The tech-laced Nasdaq Composite .IXIC rallied 30.46 points , or 2.04 percent , to 1,520.15 .",
            "The DVD CCA appealed that decision to the U.S. Supreme Court .",
        ],
        "label": [1, 1, 0, 1],
        "idx": [4, 5, 6, 7],
    }
    dev_dataset = pd.DataFrame(dev_data)

    custom_sent_keys = ["sentence1", "sentence2"]
    label_key = "label"

    X_train = train_dataset[custom_sent_keys]
    y_train = train_dataset[label_key]

    X_val = dev_dataset[custom_sent_keys]
    y_val = dev_dataset[label_key]

    automl = AutoML()

    # testing when max_iter=1 and do retrain only without hpo

    automl_settings = {
        "gpu_per_trial": 0,
        "max_iter": 1,
        "time_budget": 5,
        "task": "seq-classification",
        "metric": custom_metric,
        "log_file_name": "seqclass.log",
    }

    automl_settings["hf_args"] = {
        "model_path": "google/electra-small-discriminator",
        "output_dir": "data/output/",
        "ckpt_per_epoch": 1,
        "fp16": False,
    }

    try:
        automl.fit(
            X_train=X_train,
            y_train=y_train,
            X_val=X_val,
            y_val=y_val,
            **automl_settings
        )
    except requests.exceptions.HTTPError:
        return

    # testing calling custom metric in TransformersEstimator._compute_metrics_by_dataset_name

    automl_settings["max_iter"] = 3
    automl.fit(
        X_train=X_train, y_train=y_train, X_val=X_val, y_val=y_val, **automl_settings
    )

    del automl


if __name__ == "__main__":
    test_custom_metric()
