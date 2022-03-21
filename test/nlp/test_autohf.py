import sys
import pytest
import pickle
import shutil
import requests


@pytest.mark.skipif(sys.platform == "darwin", reason="do not run on mac os")
def test_hf_data():
    from flaml import AutoML
    import pandas as pd

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

    test_data = {
        "sentence1": [
            "That compared with $ 35.18 million , or 24 cents per share , in the year-ago period .",
            "Shares of Genentech , a much larger company with several products on the market , rose more than 2 percent .",
            "Legislation making it harder for consumers to erase their debts in bankruptcy court won overwhelming House approval in March .",
            "The Nasdaq composite index increased 10.73 , or 0.7 percent , to 1,514.77 .",
        ],
        "sentence2": [
            "Earnings were affected by a non-recurring $ 8 million tax benefit in the year-ago period .",
            "Shares of Xoma fell 16 percent in early trade , while shares of Genentech , a much larger company with several products on the market , were up 2 percent .",
            "Legislation making it harder for consumers to erase their debts in bankruptcy court won speedy , House approval in March and was endorsed by the White House .",
            "The Nasdaq Composite index , full of technology stocks , was lately up around 18 points .",
        ],
        "label": [0, 0, 0, 0],
        "idx": [8, 10, 11, 12],
    }
    test_dataset = pd.DataFrame(test_data)

    custom_sent_keys = ["sentence1", "sentence2"]
    label_key = "label"

    X_train = train_dataset[custom_sent_keys]
    y_train = train_dataset[label_key]

    X_val = dev_dataset[custom_sent_keys]
    y_val = dev_dataset[label_key]

    X_test = test_dataset[custom_sent_keys]

    automl = AutoML()

    automl_settings = {
        "gpu_per_trial": 0,
        "max_iter": 3,
        "time_budget": 10,
        "task": "seq-classification",
        "metric": "accuracy",
        "log_file_name": "seqclass.log",
        "use_ray": False,
    }

    automl_settings["hf_args"] = {
        "model_path": "google/electra-small-discriminator",
        "output_dir": "test/data/output/",
        "ckpt_per_epoch": 5,
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

    automl = AutoML()
    automl.retrain_from_log(
        X_train=X_train,
        y_train=y_train,
        train_full=True,
        record_id=0,
        **automl_settings
    )
    with open("automl.pkl", "wb") as f:
        pickle.dump(automl, f, pickle.HIGHEST_PROTOCOL)
    with open("automl.pkl", "rb") as f:
        automl = pickle.load(f)
    automl.predict(X_test)
    automl.predict(["test test", "test test"])
    automl.predict(
        [
            ["test test", "test test"],
            ["test test", "test test"],
            ["test test", "test test"],
        ]
    )

    automl.predict_proba(X_test)
    print(automl.classes_)


def _test_custom_data():
    from flaml import AutoML
    import requests
    import pandas as pd

    try:
        train_dataset = pd.read_csv("data/input/train.tsv", delimiter="\t", quoting=3)
        dev_dataset = pd.read_csv("data/input/dev.tsv", delimiter="\t", quoting=3)
        test_dataset = pd.read_csv("data/input/test.tsv", delimiter="\t", quoting=3)
    except requests.exceptions.HTTPError:
        return

    custom_sent_keys = ["#1 String", "#2 String"]
    label_key = "Quality"

    X_train = train_dataset[custom_sent_keys]
    y_train = train_dataset[label_key]

    X_val = dev_dataset[custom_sent_keys]
    y_val = dev_dataset[label_key]

    X_test = test_dataset[custom_sent_keys]

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
        "output_dir": "data/output/",
        "ckpt_per_epoch": 1,
    }

    automl.fit(
        X_train=X_train, y_train=y_train, X_val=X_val, y_val=y_val, **automl_settings
    )
    automl.predict(X_test)
    automl.predict(["test test"])
    automl.predict(
        [
            ["test test", "test test"],
            ["test test", "test test"],
            ["test test", "test test"],
        ]
    )

    import pickle

    automl.pickle("automl.pkl")

    with open("automl.pkl", "rb") as f:
        automl = pickle.load(f)
    config = automl.best_config.copy()
    config["learner"] = automl.best_estimator
    automl.trainable(config)


if __name__ == "__main__":
    test_hf_data()
