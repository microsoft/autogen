import torch
import thop
import torch.nn as nn
import torch.nn.functional as F
import torchvision
from flaml import tune
from collections import defaultdict
import math
import numpy as np

DEVICE = torch.device("cpu")
BATCHSIZE = 128
N_TRAIN_EXAMPLES = BATCHSIZE * 30
N_VALID_EXAMPLES = BATCHSIZE * 10


def _BraninCurrin(config):
    # Rescale brain
    x_1 = 15 * config["x1"] - 5
    x_2 = 15 * config["x2"]
    # Brain function
    t1 = x_2 - 5.1 / (4 * math.pi**2) * x_1**2 + 5 / math.pi * x_1 - 6
    t2 = 10 * (1 - 1 / (8 * math.pi)) * math.cos(x_1)
    brain_result = t1**2 + t2 + 10
    # Currin function
    xc_1 = config["x1"]
    xc_2 = config["x2"]
    factor1 = 1 - math.exp(-1 / (2 * xc_2))
    numer = 2300 * pow(xc_1, 3) + 1900 * pow(xc_1, 2) + 2092 * xc_1 + 60
    denom = 100 * pow(xc_1, 3) + 500 * pow(xc_1, 2) + 4 * xc_1 + 20
    currin_result = factor1 * numer / denom
    return {"brain": brain_result, "currin": currin_result}


def test_lexiflow():
    train_dataset = torchvision.datasets.FashionMNIST(
        "test/data",
        train=True,
        download=True,
        transform=torchvision.transforms.ToTensor(),
    )

    train_loader = torch.utils.data.DataLoader(
        torch.utils.data.Subset(train_dataset, list(range(N_TRAIN_EXAMPLES))),
        batch_size=BATCHSIZE,
        shuffle=True,
    )

    val_dataset = torchvision.datasets.FashionMNIST(
        "test/data", train=False, transform=torchvision.transforms.ToTensor()
    )

    val_loader = torch.utils.data.DataLoader(
        torch.utils.data.Subset(val_dataset, list(range(N_VALID_EXAMPLES))),
        batch_size=BATCHSIZE,
        shuffle=True,
    )

    def define_model(configuration):
        n_layers = configuration["n_layers"]
        layers = []
        in_features = 28 * 28
        for i in range(n_layers):
            out_features = configuration["n_units_l{}".format(i)]
            layers.append(nn.Linear(in_features, out_features))
            layers.append(nn.ReLU())
            p = configuration["dropout_{}".format(i)]
            layers.append(nn.Dropout(p))
            in_features = out_features
        layers.append(nn.Linear(in_features, 10))
        layers.append(nn.LogSoftmax(dim=1))
        return nn.Sequential(*layers)

    def train_model(model, optimizer, train_loader):
        model.train()
        for batch_idx, (data, target) in enumerate(train_loader):
            data, target = data.view(-1, 28 * 28).to(DEVICE), target.to(DEVICE)
            optimizer.zero_grad()
            F.nll_loss(model(data), target).backward()
            optimizer.step()

    def eval_model(model, valid_loader):
        model.eval()
        correct = 0
        with torch.no_grad():
            for batch_idx, (data, target) in enumerate(valid_loader):
                data, target = data.view(-1, 28 * 28).to(DEVICE), target.to(DEVICE)
                pred = model(data).argmax(dim=1, keepdim=True)
                correct += pred.eq(target.view_as(pred)).sum().item()

        accuracy = correct / N_VALID_EXAMPLES
        flops, params = thop.profile(
            model, inputs=(torch.randn(1, 28 * 28).to(DEVICE),), verbose=False
        )
        return np.log2(flops), 1 - accuracy, params

    def evaluate_function(configuration):
        model = define_model(configuration).to(DEVICE)
        optimizer = torch.optim.Adam(model.parameters(), configuration["lr"])
        n_epoch = configuration["n_epoch"]
        for epoch in range(n_epoch):
            train_model(model, optimizer, train_loader)
        flops, error_rate, params = eval_model(model, val_loader)
        return {"error_rate": error_rate, "flops": flops, "params": params}

    lexico_objectives = {}
    lexico_objectives["metrics"] = ["error_rate", "flops"]

    search_space = {
        "n_layers": tune.randint(lower=1, upper=3),
        "n_units_l0": tune.randint(lower=4, upper=128),
        "n_units_l1": tune.randint(lower=4, upper=128),
        "n_units_l2": tune.randint(lower=4, upper=128),
        "dropout_0": tune.uniform(lower=0.2, upper=0.5),
        "dropout_1": tune.uniform(lower=0.2, upper=0.5),
        "dropout_2": tune.uniform(lower=0.2, upper=0.5),
        "lr": tune.loguniform(lower=1e-5, upper=1e-1),
        "n_epoch": tune.randint(lower=1, upper=20),
    }

    low_cost_partial_config = {
        "n_layers": 1,
        "n_units_l0": 4,
        "n_units_l1": 4,
        "n_units_l2": 4,
        "n_epoch": 1,
    }

    # Non lexico tune
    analysis = tune.run(
        evaluate_function,
        metric="error_rate",
        mode="min",
        num_samples=5,
        config=search_space,
        use_ray=False,
        lexico_objectives=None,
        low_cost_partial_config=low_cost_partial_config,
    )
    print(analysis.best_trial)
    print(analysis.best_config)
    print(analysis.best_result)

    # lexico tune
    lexico_objectives["targets"] = {"error_rate": 0.0, "flops": 0.0}
    lexico_objectives["modes"] = ["min", "min"]

    # 1. lexico tune: absolute tolerance
    lexico_objectives["tolerances"] = {"error_rate": 0.02, "flops": 0.0}
    analysis = tune.run(
        evaluate_function,
        num_samples=5,
        config=search_space,
        use_ray=False,
        lexico_objectives=lexico_objectives,
        low_cost_partial_config=low_cost_partial_config,
    )
    print(analysis.best_trial)
    print(analysis.best_config)
    print(analysis.best_result)

    # 2. lexico tune: percentage tolerance
    lexico_objectives["tolerances"] = {"error_rate": "10%", "flops": "0%"}
    analysis = tune.run(
        evaluate_function,
        num_samples=5,
        config=search_space,
        use_ray=False,
        lexico_objectives=lexico_objectives,
        low_cost_partial_config=low_cost_partial_config,
    )
    print(analysis.best_trial)
    print(analysis.best_config)
    print(analysis.best_result)


def test_lexiflow_performance():
    lexico_objectives = {}
    lexico_objectives["metrics"] = ["brain", "currin"]
    lexico_objectives["tolerances"] = {"brain": 10.0, "currin": 0.0}
    lexico_objectives["targets"] = {"brain": 0.0, "currin": 0.0}
    lexico_objectives["modes"] = ["min", "min"]

    search_space = {
        "x1": tune.uniform(lower=0.000001, upper=1.0),
        "x2": tune.uniform(lower=0.000001, upper=1.0),
    }

    analysis = tune.run(
        _BraninCurrin,
        num_samples=1000,
        config=search_space,
        use_ray=False,
        lexico_objectives=lexico_objectives,
    )

    print(analysis.best_trial)
    print(analysis.best_config)
    print(analysis.best_result)

    assert (
        analysis.best_result["currin"] <= 2.2
    ), "the value of currin function should be less than 2.2"


if __name__ == "__main__":
    test_lexiflow()
    test_lexiflow_performance()
