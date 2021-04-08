'''Require: pip install torchvision ray flaml[blendsearch]
'''
import unittest
import os
import time

import logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.FileHandler('test/tune_pytorch_cifar10.log'))


try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    import torch.optim as optim
    from torch.utils.data import random_split
    import torchvision
    import torchvision.transforms as transforms

    # __net_begin__
    class Net(nn.Module):

        def __init__(self, l1=120, l2=84):
            super(Net, self).__init__()
            self.conv1 = nn.Conv2d(3, 6, 5)
            self.pool = nn.MaxPool2d(2, 2)
            self.conv2 = nn.Conv2d(6, 16, 5)
            self.fc1 = nn.Linear(16 * 5 * 5, l1)
            self.fc2 = nn.Linear(l1, l2)
            self.fc3 = nn.Linear(l2, 10)

        def forward(self, x):
            x = self.pool(F.relu(self.conv1(x)))
            x = self.pool(F.relu(self.conv2(x)))
            x = x.view(-1, 16 * 5 * 5)
            x = F.relu(self.fc1(x))
            x = F.relu(self.fc2(x))
            x = self.fc3(x)
            return x
    # __net_end__
except ImportError:
    print("skip test_pytorch because torchvision cannot be imported.")


# __load_data_begin__
def load_data(data_dir="test/data"):
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
    ])

    trainset = torchvision.datasets.CIFAR10(
        root=data_dir, train=True, download=True, transform=transform)

    testset = torchvision.datasets.CIFAR10(
        root=data_dir, train=False, download=True, transform=transform)

    return trainset, testset
# __load_data_end__


# __train_begin__
def train_cifar(config, checkpoint_dir=None, data_dir=None):
    if "l1" not in config:
        logger.warning(config)
    net = Net(2 ** config["l1"], 2 ** config["l2"])

    device = "cpu"
    if torch.cuda.is_available():
        device = "cuda:0"
        if torch.cuda.device_count() > 1:
            net = nn.DataParallel(net)
    net.to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.SGD(net.parameters(), lr=config["lr"], momentum=0.9)

    # The `checkpoint_dir` parameter gets passed by Ray Tune when a checkpoint
    # should be restored.
    if checkpoint_dir:
        checkpoint = os.path.join(checkpoint_dir, "checkpoint")
        model_state, optimizer_state = torch.load(checkpoint)
        net.load_state_dict(model_state)
        optimizer.load_state_dict(optimizer_state)

    trainset, testset = load_data(data_dir)

    test_abs = int(len(trainset) * 0.8)
    train_subset, val_subset = random_split(
        trainset, [test_abs, len(trainset) - test_abs])

    trainloader = torch.utils.data.DataLoader(
        train_subset,
        batch_size=int(2**config["batch_size"]),
        shuffle=True,
        num_workers=4)
    valloader = torch.utils.data.DataLoader(
        val_subset,
        batch_size=int(2**config["batch_size"]),
        shuffle=True,
        num_workers=4)

    from ray import tune

    for epoch in range(int(round(config["num_epochs"]))):  # loop over the dataset multiple times
        running_loss = 0.0
        epoch_steps = 0
        for i, data in enumerate(trainloader, 0):
            # get the inputs; data is a list of [inputs, labels]
            inputs, labels = data
            inputs, labels = inputs.to(device), labels.to(device)

            # zero the parameter gradients
            optimizer.zero_grad()

            # forward + backward + optimize
            outputs = net(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            # print statistics
            running_loss += loss.item()
            epoch_steps += 1
            if i % 2000 == 1999:  # print every 2000 mini-batches
                print("[%d, %5d] loss: %.3f" % (epoch + 1, i + 1,
                                                running_loss / epoch_steps))
                running_loss = 0.0

        # Validation loss
        val_loss = 0.0
        val_steps = 0
        total = 0
        correct = 0
        for i, data in enumerate(valloader, 0):
            with torch.no_grad():
                inputs, labels = data
                inputs, labels = inputs.to(device), labels.to(device)

                outputs = net(inputs)
                _, predicted = torch.max(outputs.data, 1)
                total += labels.size(0)
                correct += (predicted == labels).sum().item()

                loss = criterion(outputs, labels)
                val_loss += loss.cpu().numpy()
                val_steps += 1

        # Here we save a checkpoint. It is automatically registered with
        # Ray Tune and will potentially be passed as the `checkpoint_dir`
        # parameter in future iterations.
        with tune.checkpoint_dir(step=epoch) as checkpoint_dir:
            path = os.path.join(checkpoint_dir, "checkpoint")
            torch.save(
                (net.state_dict(), optimizer.state_dict()), path)

        tune.report(loss=(val_loss / val_steps), accuracy=correct / total)
    print("Finished Training")
# __train_end__


# __test_acc_begin__
def _test_accuracy(net, device="cpu"):
    trainset, testset = load_data()

    testloader = torch.utils.data.DataLoader(
        testset, batch_size=4, shuffle=False, num_workers=2)

    correct = 0
    total = 0
    with torch.no_grad():
        for data in testloader:
            images, labels = data
            images, labels = images.to(device), labels.to(device)
            outputs = net(images)
            _, predicted = torch.max(outputs.data, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

    return correct / total
# __test_acc_end__


# __main_begin__
def cifar10_main(
    method='BlendSearch', num_samples=10, max_num_epochs=100, gpus_per_trial=2
):
    data_dir = os.path.abspath("test/data")
    load_data(data_dir)  # Download data for all trials before starting the run
    if method == 'BlendSearch':
        from flaml import tune
    else:
        from ray import tune
    if method in ['BlendSearch', 'BOHB', 'Optuna']:
        config = {
            "l1": tune.randint(2, 8),
            "l2": tune.randint(2, 8),
            "lr": tune.loguniform(1e-4, 1e-1),
            "num_epochs": tune.qloguniform(1, max_num_epochs, q=1),
            "batch_size": tune.randint(1, 4)
        }
    else:
        config = {
            "l1": tune.randint(2, 9),
            "l2": tune.randint(2, 9),
            "lr": tune.loguniform(1e-4, 1e-1),
            "num_epochs": tune.qloguniform(1, max_num_epochs + 1, q=1),
            "batch_size": tune.randint(1, 5)
        }
    import ray
    time_budget_s = 3600
    start_time = time.time()
    if method == 'BlendSearch':
        result = tune.run(
            ray.tune.with_parameters(train_cifar, data_dir=data_dir),
            config=config,
            low_cost_partial_config={
                "l1": 2,
                "l2": 2,
                "num_epochs": 1,
                "batch_size": 4,
            },
            metric="loss",
            mode="min",
            max_resource=max_num_epochs,
            min_resource=1,
            report_intermediate_result=True,
            resources_per_trial={"cpu": 2, "gpu": gpus_per_trial},
            local_dir='logs/',
            num_samples=num_samples,
            time_budget_s=time_budget_s,
            use_ray=True)
    else:
        if 'ASHA' == method:
            algo = None
        elif 'BOHB' == method:
            from ray.tune.schedulers import HyperBandForBOHB
            from ray.tune.suggest.bohb import TuneBOHB
            algo = TuneBOHB()
            scheduler = HyperBandForBOHB(max_t=max_num_epochs)
        elif 'Optuna' == method:
            from ray.tune.suggest.optuna import OptunaSearch
            algo = OptunaSearch()
        elif 'CFO' == method:
            from flaml import CFO
            algo = CFO(low_cost_partial_config={
                "l1": 2,
                "l2": 2,
                "num_epochs": 1,
                "batch_size": 4,
            })
        elif 'Nevergrad' == method:
            from ray.tune.suggest.nevergrad import NevergradSearch
            import nevergrad as ng
            algo = NevergradSearch(optimizer=ng.optimizers.OnePlusOne)
        if method != 'BOHB':
            from ray.tune.schedulers import ASHAScheduler
            scheduler = ASHAScheduler(
                max_t=max_num_epochs,
                grace_period=1)
        result = tune.run(
            tune.with_parameters(train_cifar, data_dir=data_dir),
            resources_per_trial={"cpu": 2, "gpu": gpus_per_trial},
            config=config,
            metric="loss",
            mode="min",
            num_samples=num_samples, time_budget_s=time_budget_s,
            scheduler=scheduler, search_alg=algo
        )
    ray.shutdown()

    logger.info(f"method={method}")
    logger.info(f"n_samples={num_samples}")
    logger.info(f"time={time.time()-start_time}")
    best_trial = result.get_best_trial("loss", "min", "all")
    logger.info("Best trial config: {}".format(best_trial.config))
    logger.info("Best trial final validation loss: {}".format(
        best_trial.metric_analysis["loss"]["min"]))
    logger.info("Best trial final validation accuracy: {}".format(
        best_trial.metric_analysis["accuracy"]["max"]))

    best_trained_model = Net(2**best_trial.config["l1"],
                             2**best_trial.config["l2"])
    device = "cpu"
    if torch.cuda.is_available():
        device = "cuda:0"
        if gpus_per_trial > 1:
            best_trained_model = nn.DataParallel(best_trained_model)
    best_trained_model.to(device)

    checkpoint_path = os.path.join(best_trial.checkpoint.value, "checkpoint")

    model_state, optimizer_state = torch.load(checkpoint_path)
    best_trained_model.load_state_dict(model_state)

    test_acc = _test_accuracy(best_trained_model, device)
    logger.info("Best trial test set accuracy: {}".format(test_acc))
# __main_end__


gpus_per_trial = 0  # 0.5 on GPU server
num_samples = 500


def _test_cifar10_bs():
    cifar10_main(num_samples=num_samples, gpus_per_trial=gpus_per_trial)


def _test_cifar10_cfo():
    cifar10_main('CFO',
                 num_samples=num_samples, gpus_per_trial=gpus_per_trial)


def _test_cifar10_optuna():
    cifar10_main('Optuna',
                 num_samples=num_samples, gpus_per_trial=gpus_per_trial)


def _test_cifar10_asha():
    cifar10_main('ASHA',
                 num_samples=num_samples, gpus_per_trial=gpus_per_trial)


def _test_cifar10_bohb():
    cifar10_main('BOHB',
                 num_samples=num_samples, gpus_per_trial=gpus_per_trial)


def _test_cifar10_nevergrad():
    cifar10_main('Nevergrad',
                 num_samples=num_samples, gpus_per_trial=gpus_per_trial)


if __name__ == "__main__":
    unittest.main()
