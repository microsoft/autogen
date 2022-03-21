import sys
import pytest


@pytest.mark.skipif(sys.platform == "darwin", reason="do not run on mac os")
def test_cv():
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

    custom_sent_keys = ["sentence1", "sentence2"]
    label_key = "label"

    X_train = train_dataset[custom_sent_keys]
    y_train = train_dataset[label_key]

    automl = AutoML()

    automl_settings = {
        "gpu_per_trial": 0,
        "max_iter": 3,
        "time_budget": 5,
        "task": "seq-classification",
        "metric": "accuracy",
        "n_splits": 3,
    }

    automl_settings["hf_args"] = {
        "model_path": "google/electra-small-discriminator",
        "output_dir": "test/data/output/",
        "ckpt_per_epoch": 1,
        "fp16": False,
    }

    try:
        automl.fit(X_train=X_train, y_train=y_train, **automl_settings)
    except requests.exceptions.HTTPError:
        return


if __name__ == "__main__":
    test_cv()
