from sklearn.datasets import make_classification
import numpy as np
from pandas import DataFrame
from datetime import datetime
from flaml.model import (
    KNeighborsEstimator,
    LRL2Classifier,
    BaseEstimator,
    LGBMEstimator,
    CatBoostEstimator,
    XGBoostEstimator,
    RandomForestEstimator,
    Prophet,
    ARIMA,
    LGBM_TS_Regressor,
)


def test_lrl2():
    BaseEstimator.search_space(1, "")
    X, y = make_classification(100000, 1000)
    print("start")
    lr = LRL2Classifier()
    lr.predict(X)
    lr.fit(X, y, budget=1e-5)


def test_prep():
    X = np.array(
        list(
            zip(
                [
                    3.0,
                    16.0,
                    10.0,
                    12.0,
                    3.0,
                    14.0,
                    11.0,
                    12.0,
                    5.0,
                    14.0,
                    20.0,
                    16.0,
                    15.0,
                    11.0,
                ],
                [
                    "a",
                    "b",
                    "a",
                    "c",
                    "c",
                    "b",
                    "b",
                    "b",
                    "b",
                    "a",
                    "b",
                    1.0,
                    1.0,
                    "a",
                ],
            )
        ),
        dtype=object,
    )
    y = np.array([0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1])
    lr = LRL2Classifier()
    lr.fit(X, y)
    lr.predict(X)
    lgbm = LGBMEstimator(n_estimators=4)
    lgbm.fit(X, y)
    cat = CatBoostEstimator(n_estimators=4)
    cat.fit(X, y)
    knn = KNeighborsEstimator(task="regression")
    knn.fit(X, y)
    xgb = XGBoostEstimator(n_estimators=4, max_leaves=4)
    xgb.fit(X, y)
    xgb.predict(X)
    rf = RandomForestEstimator(task="regression", n_estimators=4, criterion="gini")
    rf.fit(X, y)

    prophet = Prophet()
    try:
        prophet.predict(4)
    except ValueError:
        # predict() with steps is only supported for arima/sarimax.
        pass
    prophet.predict(X)

    arima = ARIMA()
    arima.predict(X)
    arima._model = False
    try:
        arima.predict(X)
    except ValueError:
        # X_test needs to be either a pandas Dataframe with dates as the first column or an int number of periods for predict().
        pass

    lgbm = LGBM_TS_Regressor(optimize_for_horizon=True, lags=1)
    X = DataFrame(
        {
            "A": [
                datetime(1900, 2, 3),
                datetime(1900, 3, 4),
                datetime(1900, 3, 4),
                datetime(1900, 3, 4),
                datetime(1900, 7, 2),
                datetime(1900, 8, 9),
            ],
        }
    )
    y = np.array([0, 1, 0, 1, 0, 0])
    lgbm.predict(X[:2])
    lgbm.fit(X, y, period=2)
    lgbm.predict(X[:2])
