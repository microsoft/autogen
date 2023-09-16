import logging
import time
from typing import List

import pandas as pd
import numpy as np
from scipy.sparse import issparse
from sklearn.model_selection import (
    GroupKFold,
    TimeSeriesSplit,
)

from flaml.automl.ml import get_val_loss, default_cv_score_agg_func
from flaml.automl.time_series.ts_data import (
    TimeSeriesDataset,
    DataTransformerTS,
    normalize_ts_data,
)

from flaml.automl.task.task import (
    Task,
    get_classification_objective,
    TS_FORECAST,
    TS_FORECASTPANEL,
)

logger = logging.getLogger(__name__)


class TimeSeriesTask(Task):
    @property
    def estimators(self):
        if self._estimators is None:
            # put this into a function to avoid circular dependency
            from flaml.automl.time_series import (
                XGBoost_TS,
                XGBoostLimitDepth_TS,
                RF_TS,
                LGBM_TS,
                ExtraTrees_TS,
                CatBoost_TS,
                Prophet,
                Orbit,
                ARIMA,
                SARIMAX,
                TemporalFusionTransformerEstimator,
                HoltWinters,
            )

            self._estimators = {
                "xgboost": XGBoost_TS,
                "xgb_limitdepth": XGBoostLimitDepth_TS,
                "rf": RF_TS,
                "lgbm": LGBM_TS,
                "extra_tree": ExtraTrees_TS,
                "arima": ARIMA,
                "sarimax": SARIMAX,
                "holt-winters": HoltWinters,
                "catboost": CatBoost_TS,
                "tft": TemporalFusionTransformerEstimator,
            }

            try:
                from prophet import Prophet as foo

                self._estimators["prophet"] = Prophet
            except ImportError:
                logger.info("Couldn't import Prophet, skipping")

            try:
                from orbit.models import DLT

                self._estimators["orbit"] = Orbit
            except ImportError:
                logger.info("Couldn't import Prophet, skipping")

        return self._estimators

    # processed
    def validate_data(
        self,
        automl,
        state,
        X_train_all,
        y_train_all,
        dataframe,
        label,
        X_val=None,
        y_val=None,
        groups_val=None,
        groups=None,
    ):
        # first beat the data into a TimeSeriesDataset shape
        if isinstance(X_train_all, TimeSeriesDataset):
            # in this case, we're most likely being called by another FLAML instance
            # so all the preliminary cleaning has already been done
            pre_data = X_train_all
            val_len = len(pre_data.X_val)
        else:
            if label is None and dataframe is not None:
                raise ValueError("If data is specified via dataframe parameter, you must also specify label")

            if isinstance(y_train_all, pd.Series):
                label = y_train_all.name
            elif isinstance(y_train_all, np.ndarray):
                label = "y"  # Prophet convention

            if isinstance(label, str):
                target_names = [label]
            else:
                target_names = label

            if self.time_col is None:
                if isinstance(X_train_all, pd.DataFrame):
                    assert dataframe is None, "One of dataframe and X arguments must be None"
                    self.time_col = X_train_all.columns[0]
                elif dataframe is not None:
                    assert X_train_all is None, "One of dataframe and X arguments must be None"
                    self.time_col = dataframe.columns[0]
                else:
                    self.time_col = "ds"

            automl._df = True

            if X_train_all is not None:
                assert y_train_all is not None, "If X_train_all is not None, y_train_all must also be"
                assert dataframe is None, "If X_train_all is provided, dataframe must be None"
                dataframe = TimeSeriesDataset.to_dataframe(X_train_all, y_train_all, target_names, self.time_col)

            elif dataframe is not None:
                assert label is not None, "A label or list of labels must be provided."
                assert isinstance(dataframe, pd.DataFrame), "dataframe must be a pandas DataFrame"
                assert label in dataframe.columns, f"{label} must a column name in dataframe"
            else:
                raise ValueError("Must supply either X_train_all and y_train_all, or dataframe and label")

            try:
                dataframe[self.time_col] = pd.to_datetime(dataframe[self.time_col])
            except Exception:
                raise ValueError(
                    f"For '{TS_FORECAST}' task, time column {self.time_col} must contain timestamp values."
                )

            dataframe = remove_ts_duplicates(dataframe, self.time_col)

            if X_val is not None:
                assert y_val is not None, "If X_val is not None, y_val must also be"
                val_df = TimeSeriesDataset.to_dataframe(X_val, y_val, target_names, self.time_col)
                val_len = len(val_df)
            else:
                val_len = 0
                val_df = None

            pre_data = TimeSeriesDataset(
                train_data=dataframe,
                time_col=self.time_col,
                target_names=target_names,
                test_data=val_df,
            )

        # TODO: should the transformer be a property of the dataset instead?
        automl._transformer = DataTransformerTS(self.time_col, label)
        Xt, yt = automl._transformer.fit_transform(pre_data.X_all, pre_data.y_all)

        df_t = pd.concat([Xt, yt], axis=1)

        data = TimeSeriesDataset(
            train_data=df_t,
            time_col=pre_data.time_col,
            target_names=pre_data.target_names,
        ).move_validation_boundary(-val_len)

        # now setup the properties of all the other relevant objects

        # TODO: where are these used? Replace with pointers to data?
        automl._X_train_all, automl._y_train_all = Xt, yt

        # TODO: where are these used?
        automl._nrow, automl._ndim = data.X_train.shape

        # make a property instead? Or just fix the call?
        automl._label_transformer = automl._transformer.label_transformer

        automl._feature_names_in_ = (
            automl._X_train_all.columns.to_list() if hasattr(automl._X_train_all, "columns") else None
        )

        self.time_col = data.time_col
        self.target_names = data.target_names

        automl._state.X_val = data
        automl._state.X_train = data
        automl._state.y_train = None
        automl._state.y_val = None
        if data.test_data is not None and len(data.test_data) > 0:
            automl._state.X_train_all = data.move_validation_boundary(len(data.test_data))
        else:
            automl._state.X_train_all = data
        automl._state.y_train_all = None

        automl._state.data_size = data.train_data.shape
        automl.data_size_full = len(data.all_data)
        automl._state.groups = None
        automl._sample_weight_full = None

    def prepare_data(
        self,
        state,
        X_train_all,
        y_train_all,
        auto_argument,
        eval_method,
        split_type,
        split_ratio,
        n_splits,
        data_is_df,
        sample_weight_full,
        time_col=None,
    ):
        state.kf = None
        state.data_size_full = len(y_train_all)

        if split_type in ["uniform", "stratified"]:
            raise ValueError(f"Split type {split_type} is not valid for time series")

        state.groups = None
        state.groups_all = None
        state.groups_val = None

        ts_data = state.X_val
        no_test_data = ts_data is None or ts_data.test_data is None or len(ts_data.test_data) == 0
        if no_test_data and eval_method == "holdout":
            # NOTE: _prepare_data is before kwargs is updated to fit_kwargs_by_estimator
            period = state.fit_kwargs["period"]

            if self.name == TS_FORECASTPANEL:
                # TODO: move this into the TimeSeriesDataset class
                X_train_all = ts_data.X_train
                y_train_all = ts_data.y_train

                X_train_all["time_idx"] -= X_train_all["time_idx"].min()
                X_train_all["time_idx"] = X_train_all["time_idx"].astype("int")
                ids = state.fit_kwargs["group_ids"].copy()
                ids.append(ts_data.time_col)
                ids.append("time_idx")
                y_train_all = pd.DataFrame(y_train_all)
                y_train_all[ids] = X_train_all[ids]
                X_train_all = X_train_all.sort_values(ids)
                y_train_all = y_train_all.sort_values(ids)
                training_cutoff = X_train_all["time_idx"].max() - period
                X_train = X_train_all[lambda x: x.time_idx <= training_cutoff]
                y_train = y_train_all[lambda x: x.time_idx <= training_cutoff].drop(columns=ids)
                X_val = X_train_all[lambda x: x.time_idx > training_cutoff]
                y_val = y_train_all[lambda x: x.time_idx > training_cutoff].drop(columns=ids)

                train_data = normalize_ts_data(
                    X_train,
                    ts_data.target_names,
                    ts_data.time_col,
                    y_train,
                )
                test_data = normalize_ts_data(
                    X_val,
                    ts_data.target_names,
                    ts_data.time_col,
                    y_val,
                )
                ts_data = TimeSeriesDataset(
                    train_data,
                    ts_data.time_col,
                    ts_data.target_names,
                    ts_data.frequency,
                    test_data,
                )
                state.X_val = ts_data
                state.X_train = ts_data

            else:
                # if eval_method = holdout, make holdout data
                num_samples = ts_data.train_data.shape[0]
                assert period < num_samples, f"period={period}>#examples={num_samples}"
                state.X_val = ts_data.move_validation_boundary(-period)
                state.X_train = state.X_val

        if eval_method != "holdout":
            if self.name != TS_FORECASTPANEL:
                period = state.fit_kwargs[
                    "period"
                ]  # NOTE: _prepare_data is before kwargs is updated to fit_kwargs_by_estimator
                step_size = state.fit_kwargs.get("cv_step_size", period)

                ts_data = state.X_train
                if n_splits * step_size + 2 * period > ts_data.y_train.size:
                    n_splits = int((ts_data.y_train.size - 2 * period) / step_size)
                    assert n_splits >= 2, (
                        f"cross validation for forecasting period={period}"
                        f" requires input data with at least {2*period + 2*step_size} examples."
                    )
                    logger.info(f"Using nsplits={n_splits} due to data size limit.")
                state.kf = TimeSeriesSplit(n_splits=n_splits, test_size=period)
                state.kf.step_size = step_size

            else:
                n_groups = ts_data.X_train.groupby(state.fit_kwargs.get("group_ids")).ngroups
                period = state.fit_kwargs["period"]
                state.kf = TimeSeriesSplit(n_splits=n_splits, test_size=period * n_groups)

    # TODO: move task detection to Task.__init__!
    def decide_split_type(
        self,
        split_type,
        y_train_all,
        fit_kwargs,
        groups=None,
    ) -> str:
        # TODO: move into task creation!!!
        if self.name == "classification":
            self.name = get_classification_objective(len(np.unique(y_train_all)))

        # TODO: do we need this?
        if not isinstance(split_type, str):
            assert hasattr(split_type, "split") and hasattr(
                split_type, "get_n_splits"
            ), "split_type must be a string or a splitter object with split and get_n_splits methods."
            assert (
                not isinstance(split_type, GroupKFold) or groups is not None
            ), "GroupKFold requires groups to be provided."
            return split_type

        else:
            assert split_type in ["auto", "time"]
            assert isinstance(
                fit_kwargs.get("period"),
                int,  # NOTE: _decide_split_type is before kwargs is updated to fit_kwargs_by_estimator
            ), f"missing a required integer 'period' for '{TS_FORECAST}' task."
            if fit_kwargs.get("group_ids"):
                # TODO (MARK) This will likely not play well with the task class
                self.name = TS_FORECASTPANEL
                assert isinstance(
                    fit_kwargs.get("group_ids"), list
                ), f"missing a required List[str] 'group_ids' for '{TS_FORECASTPANEL}' task."
            return "time"

    # TODO: merge with preprocess() below
    def _preprocess(self, X, transformer=None):
        if isinstance(X, List):
            try:
                if isinstance(X[0], List):
                    X = [x for x in zip(*X)]
                X = pd.DataFrame(
                    dict(
                        [
                            (transformer._str_columns[idx], X[idx])
                            if isinstance(X[0], List)
                            else (transformer._str_columns[idx], [X[idx]])
                            for idx in range(len(X))
                        ]
                    )
                )
            except IndexError:
                raise IndexError("Test data contains more columns than training data, exiting")
        elif isinstance(X, int):
            return X
        elif issparse(X):
            X = X.tocsr()
        if self.is_ts_forecast():
            X = pd.DataFrame(X)
        if transformer:
            X = transformer.transform(X)
        return X

    def preprocess(self, X, transformer=None):
        if isinstance(X, pd.DataFrame) or isinstance(X, np.ndarray) or isinstance(X, pd.Series):
            X = X.copy()
            X = normalize_ts_data(X, self.target_names, self.time_col)
            return self._preprocess(X, transformer)
        elif isinstance(X, int):
            return X
        else:
            raise ValueError(f"unknown type of X, {X.__class__}")

    def evaluate_model_CV(
        self,
        config,
        estimator,
        X_train_all,
        y_train_all,
        budget,
        kf,
        eval_metric,
        best_val_loss,
        cv_score_agg_func=None,
        log_training_metric=False,
        fit_kwargs={},
        free_mem_ratio=0,  # what is this for?
    ):
        if cv_score_agg_func is None:
            cv_score_agg_func = default_cv_score_agg_func
        start_time = time.time()
        val_loss_folds = []
        log_metric_folds = []
        metric = None
        train_time = pred_time = 0
        total_fold_num = 0
        n = kf.get_n_splits()
        if self.is_classification():
            labels = np.unique(y_train_all)
        else:
            labels = fit_kwargs.get("label_list")  # pass the label list on to compute the evaluation metric
        ts_data = X_train_all
        budget_per_train = budget / n
        ts_data = X_train_all
        for data in ts_data.cv_train_val_sets(kf.n_splits, kf.test_size, kf.step_size):
            estimator.cleanup()
            val_loss_i, metric_i, train_time_i, pred_time_i = get_val_loss(
                config,
                estimator,
                X_train=data,
                y_train=None,
                X_val=data,
                y_val=None,
                eval_metric=eval_metric,
                labels=labels,
                budget=budget_per_train,
                log_training_metric=log_training_metric,
                fit_kwargs=fit_kwargs,
                task=self,
                weight_val=None,
                groups_val=None,
                free_mem_ratio=free_mem_ratio,
            )
            if isinstance(metric_i, dict) and "intermediate_results" in metric_i:
                del metric_i["intermediate_results"]
            total_fold_num += 1
            val_loss_folds.append(val_loss_i)
            log_metric_folds.append(metric_i)
            train_time += train_time_i
            pred_time += pred_time_i
            if time.time() - start_time >= budget:
                break
        val_loss, metric = cv_score_agg_func(val_loss_folds, log_metric_folds)
        n = total_fold_num
        pred_time /= n
        return val_loss, metric, train_time, pred_time

    def default_estimator_list(self, estimator_list: List[str], is_spark_dataframe: bool) -> List[str]:
        assert not is_spark_dataframe, "Spark is not yet supported for time series"

        # TODO: why not do this if/then in the calling function?
        if "auto" != estimator_list:
            return estimator_list

        if self.is_ts_forecastpanel():
            return ["tft"]

        estimator_list = [
            "lgbm",
            "rf",
            "xgboost",
            "extra_tree",
            "xgb_limitdepth",
        ]

        # Catboost appears to be way slower than the others, don't include it by default
        # try:
        #     import catboost
        #
        #     estimator_list.append("catboost")
        # except ImportError:
        #     pass

        if self.is_regression():
            estimator_list += ["arima", "sarimax"]

            try:
                import prophet

                estimator_list.append("prophet")
            except ImportError:
                pass

        return estimator_list

    def default_metric(self, metric: str) -> str:
        assert self.is_ts_forecast(), "If this is not a TS forecasting task, this code should never have been called"
        if metric == "auto":
            return "mape"
        else:
            return metric

    @staticmethod
    def prepare_sample_train_data(automlstate, sample_size):
        # we take the tail, rather than the head, for compatibility with time series

        shift = sample_size - len(automlstate.X_train.train_data)
        sampled_X_train = automlstate.X_train.move_validation_boundary(shift)

        return sampled_X_train, None, None, None


def remove_ts_duplicates(
    X,
    time_col,
):
    """
    Assumes the targets are included
    @param X:
    @param time_col:
    @param y:
    @return:
    """

    duplicates = X.duplicated()

    if any(duplicates):
        logger.warning("Duplicate timestamp values found in timestamp column. " f"\n{X.loc[duplicates, X][time_col]}")
        X = X.drop_duplicates()
        logger.warning("Removed duplicate rows based on all columns")
        assert (
            X[[X.columns[0]]].duplicated() is None
        ), "Duplicate timestamp values with different values for other columns."

    return X
