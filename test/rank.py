from sklearn.datasets import fetch_openml
from flaml import AutoML

X_train, y_train = fetch_openml(name="credit-g", return_X_y=True, as_frame=False)
# not a real learning to rank dataaset
groups = [200] * 4 + [100] * 2  # group counts
automl = AutoML()
automl.fit(
    X_train,
    y_train,
    groups=groups,
    task="rank",
    time_budget=1,  # in seconds
)
