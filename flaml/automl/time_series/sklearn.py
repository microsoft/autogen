try:
    import pandas as pd
    from pandas import DataFrame, Series, to_datetime
except ImportError:

    class PD:
        pass

    pd = PD()
    pd.DataFrame = None
    pd.Series = None
    DataFrame = Series = None

import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA


def make_lag_features(X: pd.DataFrame, y: pd.Series, lags: int):
    """Transform input data X, y into autoregressive form - shift
    them appropriately based on horizon and create `lags` columns.

    Parameters
    ----------
    X : pandas.DataFrame
        Input features.

    y : array_like, (1d)
        Target vector.

    horizon : int
        length of X for `predict` method

    Returns
    -------
    pandas.DataFrame
        shifted dataframe with `lags` columns
    """
    lag_features = []

    # make sure we show y's _previous_ value to exclude data leaks
    X = X.reset_index(drop=True)
    X["lag_" + y.name] = y.shift(1).values

    X_lag = X.copy()
    for i in range(0, lags):
        X_lag.columns = [f"{c}_lag_{i}" for c in X.columns]
        lag_features.append(X_lag)
        X_lag = X_lag.shift(1)

    X_lags = pd.concat(lag_features, axis=1)
    X_out = X_lags.dropna().reset_index(drop=True)
    assert len(X_out) + lags == len(X)
    return X_out


class SklearnWrapper:
    def __init__(
        self,
        model_class: type,
        horizon: int,
        lags: int,
        init_params: dict = None,
        fit_params: dict = None,
        pca_features: bool = False,
    ):
        init_params = init_params if init_params else {}
        self.fit_params = fit_params if fit_params else {}
        self.lags = lags
        self.horizon = horizon
        # TODO: use multiregression where available
        self.models = [model_class(**init_params) for _ in range(horizon)]
        self.pca_features = pca_features
        if self.pca_features:
            self.norm = StandardScaler()
            self.pca = None

    def fit(self, X: pd.DataFrame, y: pd.Series, **kwargs):
        self._X = X
        self._y = y

        fit_params = {**self.fit_params, **kwargs}
        X_feat = make_lag_features(X, y, self.lags)
        if self.pca_features:
            X_trans = self.norm.fit_transform(X_feat)

            cum_expl_var = np.cumsum(PCA(svd_solver="full").fit(X_trans).explained_variance_ratio_)
            self.pca = PCA(svd_solver="full", n_components=np.argmax(1 - cum_expl_var < 1e-6))
            X_trans = self.pca.fit_transform(X_trans)
        else:
            X_trans = X_feat

        for i, model in enumerate(self.models):
            offset = i + self.lags
            model.fit(X_trans[: len(X) - offset], y[offset:], **fit_params)
        return self

    def predict(self, X, X_train=None, y_train=None):
        if X_train is None:
            X_train = self._X
        if y_train is None:
            y_train = self._y

        X_train = X_train.reset_index(drop=True)
        X_train[self._y.name] = y_train.values
        Xall = pd.concat([X_train, X], axis=0).reset_index(drop=True)
        y = Xall.pop(self._y.name)

        X_feat = make_lag_features(Xall[: len(X_train) + 1], y[: len(X_train) + 1], self.lags)
        if self.pca_features:
            X_trans = self.pca.transform(self.norm.transform(X_feat))
        else:
            X_trans = X_feat
        # predict all horizons from the latest features vector
        preds = pd.Series([m.predict(X_trans[-1:])[0] for m in self.models])
        if len(preds) < len(X):
            # recursive call if len(X) > trained horizon
            y_train = pd.concat([y_train, preds], axis=0, ignore_index=True)
            preds = pd.concat(
                [
                    preds,
                    self.predict(
                        X=Xall[len(y_train) :],
                        X_train=Xall[: len(y_train)],
                        y_train=y_train,
                    ),
                ],
                axis=0,
                ignore_index=True,
            )
        if len(preds) > len(X):
            preds = preds[: len(X)]

        preds.index = X.index
        # TODO: do we want auto-clipping?
        # return self._clip_predictions(preds)
        return preds

    # TODO: fix
    # @staticmethod
    # def _adjust_holidays(X):
    #     """Transform 'holiday' columns to binary feature.
    #
    #     Parameters
    #     ----------
    #     X : pandas.DataFrame
    #         Input features with 'holiday' column.
    #
    #     Returns
    #     -------
    #     pandas.DataFrame
    #         Holiday feature in numeric form
    #     """
    #     return X.assign(
    #         **{col: X[col] != "" for col in X.filter(like="_holiday_").columns}
    #     )
