import sys
import pytest


@pytest.mark.skipif(sys.platform == "darwin", reason="do not run on mac os")
def test_mcc():
    from flaml import AutoML
    import requests
    import pandas as pd

    train_data = {
        "video-id": [
            "anetv_fruimvo90vA",
            "anetv_fruimvo90vA",
            "anetv_fruimvo90vA",
            "anetv_MldEr60j33M",
            "lsmdc0049_Hannah_and_her_sisters-69438",
        ],
        "fold-ind": ["10030", "10030", "10030", "5488", "17405"],
        "startphrase": [
            "A woman is seen running down a long track and jumping into a pit. The camera",
            "A woman is seen running down a long track and jumping into a pit. The camera",
            "A woman is seen running down a long track and jumping into a pit. The camera",
            "A man in a white shirt bends over and picks up a large weight. He",
            "Someone furiously shakes someone away. He",
        ],
        "sent1": [
            "A woman is seen running down a long track and jumping into a pit.",
            "A woman is seen running down a long track and jumping into a pit.",
            "A woman is seen running down a long track and jumping into a pit.",
            "A man in a white shirt bends over and picks up a large weight.",
            "Someone furiously shakes someone away.",
        ],
        "sent2": ["The camera", "The camera", "The camera", "He", "He"],
        "gold-source": ["gen", "gen", "gold", "gen", "gold"],
        "ending0": [
            "captures her as well as lifting weights down in place.",
            "follows her spinning her body around and ends by walking down a lane.",
            "watches her as she walks away and sticks her tongue out to another person.",
            "lifts the weights over his head.",
            "runs to a woman standing waiting.",
        ],
        "ending1": [
            "pans up to show another woman running down the track.",
            "pans around the two.",
            "captures her as well as lifting weights down in place.",
            "also lifts it onto his chest before hanging it back out again.",
            "tackles him into the passenger seat.",
        ],
        "ending2": [
            "follows her movements as the group members follow her instructions.",
            "captures her as well as lifting weights down in place.",
            "follows her spinning her body around and ends by walking down a lane.",
            "spins around and lifts a barbell onto the floor.",
            "pounds his fist against a cupboard.",
        ],
        "ending3": [
            "follows her spinning her body around and ends by walking down a lane.",
            "follows her movements as the group members follow her instructions.",
            "pans around the two.",
            "bends down and lifts the weight over his head.",
            "offers someone the cup on his elbow and strides out.",
        ],
        "label": [1, 3, 0, 0, 2],
    }
    dev_data = {
        "video-id": [
            "lsmdc3001_21_JUMP_STREET-422",
            "lsmdc0001_American_Beauty-45991",
            "lsmdc0001_American_Beauty-45991",
            "lsmdc0001_American_Beauty-45991",
        ],
        "fold-ind": ["11783", "10977", "10970", "10968"],
        "startphrase": [
            "Firing wildly he shoots holes through the tanker. He",
            "He puts his spatula down. The Mercedes",
            "He stands and looks around, his eyes finally landing on: "
            "The digicam and a stack of cassettes on a shelf. Someone",
            "He starts going through someone's bureau. He opens the drawer "
            "in which we know someone keeps his marijuana, but he",
        ],
        "sent1": [
            "Firing wildly he shoots holes through the tanker.",
            "He puts his spatula down.",
            "He stands and looks around, his eyes finally landing on: "
            "The digicam and a stack of cassettes on a shelf.",
            "He starts going through someone's bureau.",
        ],
        "sent2": [
            "He",
            "The Mercedes",
            "Someone",
            "He opens the drawer in which we know someone keeps his marijuana, but he",
        ],
        "gold-source": ["gold", "gold", "gold", "gold"],
        "ending0": [
            "overtakes the rig and falls off his bike.",
            "fly open and drinks.",
            "looks at someone's papers.",
            "stops one down and rubs a piece of the gift out.",
        ],
        "ending1": [
            "squeezes relentlessly on the peanut jelly as well.",
            "walks off followed driveway again.",
            "feels around it and falls in the seat once more.",
            "cuts the mangled parts.",
        ],
        "ending2": [
            "scrambles behind himself and comes in other directions.",
            "slots them into a separate green.",
            "sprints back from the wreck and drops onto his back.",
            "hides it under his hat to watch.",
        ],
        "ending3": [
            "sweeps a explodes and knocks someone off.",
            "pulls around to the drive - thru window.",
            "sits at the kitchen table, staring off into space.",
            "does n't discover its false bottom.",
        ],
        "label": [0, 3, 3, 3],
    }
    test_data = {
        "video-id": [
            "lsmdc0001_American_Beauty-45991",
            "lsmdc0001_American_Beauty-45991",
            "lsmdc0001_American_Beauty-45991",
            "lsmdc0001_American_Beauty-45991",
        ],
        "fold-ind": ["10980", "10976", "10978", "10969"],
        "startphrase": [
            "Someone leans out of the drive - thru window, "
            "grinning at her, holding bags filled with fast food. The Counter Girl",
            "Someone looks up suddenly when he hears. He",
            "Someone drives; someone sits beside her. They",
            "He opens the drawer in which we know someone "
            "keeps his marijuana, but he does n't discover"
            " its false bottom. He stands and looks around, his eyes",
        ],
        "sent1": [
            "Someone leans out of the drive - thru "
            "window, grinning at her, holding bags filled with fast food.",
            "Someone looks up suddenly when he hears.",
            "Someone drives; someone sits beside her.",
            "He opens the drawer in which we know"
            " someone keeps his marijuana, but he does n't discover its false bottom.",
        ],
        "sent2": [
            "The Counter Girl",
            "He",
            "They",
            "He stands and looks around, his eyes",
        ],
        "gold-source": ["gold", "gold", "gold", "gold"],
        "ending0": [
            "stands next to him, staring blankly.",
            "puts his spatula down.",
            "rise someone's feet up.",
            "moving to the side, the houses rapidly stained.",
        ],
        "ending1": [
            "with auditorium, filmed, singers the club.",
            "bumps into a revolver and drops surreptitiously into his weapon.",
            "lift her and they are alarmed.",
            "focused as the sight of someone making his way down a trail.",
        ],
        "ending2": [
            "attempts to block her ransacked.",
            "talks using the phone and walks away for a few seconds.",
            "are too involved with each other to "
            "notice someone watching them from the drive - thru window.",
            "finally landing on: the digicam and a stack of cassettes on a shelf.",
        ],
        "ending3": [
            "is eating solid and stinky.",
            "bundles the flaxen powder beneath the car.",
            "sit at a table with a beer from a table.",
            "deep and continuing, its bleed - length sideburns pressing on him.",
        ],
        "label": [0, 0, 2, 2],
    }

    train_dataset = pd.DataFrame(train_data)
    dev_dataset = pd.DataFrame(dev_data)
    test_dataset = pd.DataFrame(test_data)

    custom_sent_keys = [
        "sent1",
        "sent2",
        "ending0",
        "ending1",
        "ending2",
        "ending3",
        "gold-source",
        "video-id",
        "startphrase",
        "fold-ind",
    ]
    label_key = "label"

    X_train = train_dataset[custom_sent_keys]
    y_train = train_dataset[label_key]

    X_val = dev_dataset[custom_sent_keys]
    y_val = dev_dataset[label_key]

    X_test = test_dataset[custom_sent_keys]
    X_true = test_dataset[label_key]
    automl = AutoML()

    automl_settings = {
        "gpu_per_trial": 0,
        "max_iter": 2,
        "time_budget": 5,
        "task": "multichoice-classification",
        "metric": "accuracy",
        "log_file_name": "seqclass.log",
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

    y_pred = automl.predict(X_test)
    proba = automl.predict_proba(X_test)
    print(str(len(automl.classes_)) + " classes")
    print(y_pred)
    print(X_true)
    print(proba)
    true_count = 0
    for i, v in X_true.items():
        if y_pred[i] == v:
            true_count += 1
    accuracy = round(true_count / len(y_pred), 5)
    print("Accuracy: " + str(accuracy))


if __name__ == "__main__":
    test_mcc()
