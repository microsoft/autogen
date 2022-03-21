import sys
import pytest


@pytest.mark.skipif(sys.platform == "darwin", reason="do not run on mac os")
def test_regression():
    try:
        import ray

        if not ray.is_initialized():
            ray.init()
    except ImportError:
        return
    from flaml import AutoML
    import pandas as pd

    train_data = {
        "sentence1": [
            "A plane is taking off.",
            "A man is playing a large flute.",
            "A man is spreading shreded cheese on a pizza.",
            "Three men are playing chess.",
        ],
        "sentence2": [
            "An air plane is taking off.",
            "A man is playing a flute.",
            "A man is spreading shredded cheese on an uncooked pizza.",
            "Two men are playing chess.",
        ],
        "label": [5.0, 3.799999952316284, 3.799999952316284, 2.5999999046325684],
        "idx": [0, 1, 2, 3],
    }
    train_dataset = pd.DataFrame(train_data)

    dev_data = {
        "sentence1": [
            "A man is playing the cello.",
            "Some men are fighting.",
            "A man is smoking.",
            "The man is playing the piano.",
        ],
        "sentence2": [
            "A man seated is playing the cello.",
            "Two men are fighting.",
            "A man is skating.",
            "The man is playing the guitar.",
        ],
        "label": [4.25, 4.25, 0.5, 1.600000023841858],
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

    automl_settings = {
        "gpu_per_trial": 0,
        "max_iter": 2,
        "time_budget": 5,
        "task": "seq-regression",
        "metric": "pearsonr",
        "starting_points": {"transformer": {"num_train_epochs": 1}},
        "use_ray": {"local_dir": "data/outut/"},
    }

    automl_settings["hf_args"] = {
        "model_path": "google/electra-small-discriminator",
        "output_dir": "test/data/output/",
        "ckpt_per_epoch": 1,
        "fp16": False,
    }

    ray.shutdown()
    ray.init()

    automl.fit(
        X_train=X_train, y_train=y_train, X_val=X_val, y_val=y_val, **automl_settings
    )
    automl.predict(X_val)


if __name__ == "__main__":
    test_regression()
