def test_regression():
    try:
        import ray
    except ImportError:
        return
    from flaml import AutoML

    from datasets import load_dataset

    train_dataset = (
        load_dataset("glue", "stsb", split="train[:1%]").to_pandas().iloc[0:4]
    )
    dev_dataset = (
        load_dataset("glue", "stsb", split="train[1%:2%]").to_pandas().iloc[0:4]
    )

    custom_sent_keys = ["sentence1", "sentence2"]
    label_key = "label"

    X_train = train_dataset[custom_sent_keys]
    y_train = train_dataset[label_key]

    X_val = dev_dataset[custom_sent_keys]
    y_val = dev_dataset[label_key]

    automl = AutoML()

    automl_settings = {
        "gpu_per_trial": 0,
        "max_iter": 3,
        "time_budget": 20,
        "task": "seq-regression",
        "metric": "rmse",
        "model_history": True,
    }

    automl_settings["custom_hpo_args"] = {
        "model_path": "google/electra-small-discriminator",
        "output_dir": "data/output/",
        "ckpt_per_epoch": 5,
        "fp16": False,
    }

    automl.fit(
        X_train=X_train, y_train=y_train, X_val=X_val, y_val=y_val, **automl_settings
    )
