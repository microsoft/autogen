# Tune - PyTorch

This example uses flaml to tune a pytorch model on CIFAR10.

## Prepare for tuning

### Requirements
```bash
pip install torchvision "flaml[blendsearch,ray]"
```

Before we are ready for tuning, we first need to define the neural network that we would like to tune.

### Network Specification

```python
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import random_split
import torchvision
import torchvision.transforms as transforms


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
```

### Data

```python
def load_data(data_dir="data"):
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
    ])

    trainset = torchvision.datasets.CIFAR10(
        root=data_dir, train=True, download=True, transform=transform)

    testset = torchvision.datasets.CIFAR10(
        root=data_dir, train=False, download=True, transform=transform)

    return trainset, testset
```

### Training

```python
from ray import tune

def train_cifar(config, checkpoint_dir=None, data_dir=None):
    if "l1" not in config:
        logger.warning(config)
    net = Net(2**config["l1"], 2**config["l2"])

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
```

### Test Accuracy

```python
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
```

## Hyperparameter Optimization

```python
import numpy as np
import flaml
import os

data_dir = os.path.abspath("data")
load_data(data_dir)  # Download data for all trials before starting the run
```

### Search space

```python
max_num_epoch = 100
config = {
    "l1": tune.randint(2, 9),   # log transformed with base 2
    "l2": tune.randint(2, 9),   # log transformed with base 2
    "lr": tune.loguniform(1e-4, 1e-1),
    "num_epochs": tune.loguniform(1, max_num_epoch),
    "batch_size": tune.randint(1, 5)    # log transformed with base 2
}
```

### Budget and resource constraints

```python
time_budget_s = 600     # time budget in seconds
gpus_per_trial = 0.5    # number of gpus for each trial; 0.5 means two training jobs can share one gpu
num_samples = 500       # maximal number of trials
np.random.seed(7654321)
```

### Launch the tuning

```python
import time
start_time = time.time()
result = flaml.tune.run(
    tune.with_parameters(train_cifar, data_dir=data_dir),
    config=config,
    metric="loss",
    mode="min",
    low_cost_partial_config={"num_epochs": 1},
    max_resource=max_num_epoch,
    min_resource=1,
    scheduler="asha",  # Use asha scheduler to perform early stopping based on intermediate results reported
    resources_per_trial={"cpu": 1, "gpu": gpus_per_trial},
    local_dir='logs/',
    num_samples=num_samples,
    time_budget_s=time_budget_s,
    use_ray=True)
```

### Check the result

```python
print(f"#trials={len(result.trials)}")
print(f"time={time.time()-start_time}")
best_trial = result.get_best_trial("loss", "min", "all")
print("Best trial config: {}".format(best_trial.config))
print("Best trial final validation loss: {}".format(
    best_trial.metric_analysis["loss"]["min"]))
print("Best trial final validation accuracy: {}".format(
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
print("Best trial test set accuracy: {}".format(test_acc))
```

### Sample of output

```
#trials=44
time=1193.913584947586
Best trial config: {'l1': 8, 'l2': 8, 'lr': 0.0008818671030627281, 'num_epochs': 55.9513429004283, 'batch_size': 3}
Best trial final validation loss: 1.0694482081472874
Best trial final validation accuracy: 0.6389
Files already downloaded and verified
Files already downloaded and verified
Best trial test set accuracy: 0.6294
```

[Link to notebook](https://github.com/microsoft/FLAML/blob/main/notebook/tune_pytorch.ipynb) | [Open in colab](https://colab.research.google.com/github/microsoft/FLAML/blob/main/notebook/tune_pytorch.ipynb)