def test_classification_head():
    from flaml import AutoML
    import pandas as pd
    import requests

    train_data = {
        "text": [
            "i didnt feel humiliated",
            "i can go from feeling so hopeless to so damned hopeful just from being around someone who cares and is awake",
            "im grabbing a minute to post i feel greedy wrong",
            "i am ever feeling nostalgic about the fireplace i will know that it is still on the property",
            "i am feeling grouchy",
            "ive been feeling a little burdened lately wasnt sure why that was",
            "ive been taking or milligrams or times recommended amount and ive fallen asleep a lot faster but i also feel like so funny",
            "i feel as confused about life as a teenager or as jaded as a year old man",
            "i have been with petronas for years i feel that petronas has performed well and made a huge profit",
            "i feel romantic too",
            "i feel like i have to make the suffering i m seeing mean something",
            "i do feel that running is a divine experience and that i can expect to have some type of spiritual encounter",
        ],
        "label": [0, 0, 3, 2, 3, 0, 5, 4, 1, 2, 0, 1],
    }
    train_dataset = pd.DataFrame(train_data)

    dev_data = {
        "text": [
            "i think it s the easiest time of year to feel dissatisfied",
            "i feel low energy i m just thirsty",
            "i have immense sympathy with the general point but as a possible proto writer trying to find time to write in the corners of life and with no sign of an agent let alone a publishing contract this feels a little precious",
            "i do not feel reassured anxiety is on each side",
        ],
        "label": [3, 0, 1, 1],
    }
    dev_dataset = pd.DataFrame(dev_data)

    custom_sent_keys = ["text"]
    label_key = "label"

    X_train = train_dataset[custom_sent_keys]
    y_train = train_dataset[label_key]

    X_val = dev_dataset[custom_sent_keys]
    y_val = dev_dataset[label_key]

    automl = AutoML()

    automl_settings = {
        "gpu_per_trial": 0,
        "max_iter": 3,
        "time_budget": 5,
        "task": "seq-classification",
        "metric": "accuracy",
    }

    automl_settings["hf_args"] = {
        "model_path": "google/electra-small-discriminator",
        "output_dir": "test/data/output/",
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
