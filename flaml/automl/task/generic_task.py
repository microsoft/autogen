import logging
import time
from typing import List, Optional

import pandas as pd
import numpy as np
from scipy.sparse import issparse
from sklearn.utils import shuffle
from sklearn.model_selection import (
    train_test_split,
    RepeatedStratifiedKFold,
    RepeatedKFold,
    GroupKFold,
    TimeSeriesSplit,
    GroupShuffleSplit,
    StratifiedGroupKFold,
)

from flaml.automl.data import TS_TIMESTAMP_COL, concat
from flaml.automl.ml import EstimatorSubclass, default_cv_score_agg_func, get_val_loss
from flaml.automl.model import (
    XGBoostSklearnEstimator,
    XGBoostLimitDepthEstimator,
    RandomForestEstimator,
    LGBMEstimator,
    LRL1Classifier,
    LRL2Classifier,
    CatBoostEstimator,
    ExtraTreesEstimator,
    KNeighborsEstimator,
    TransformersEstimator,
    TransformersEstimatorModelSelection,
)
from flaml.automl.task.task import (
    Task,
    get_classification_objective,
    TS_FORECAST,
    TS_FORECASTPANEL,
)
from flaml.config import RANDOM_SEED

logger = logging.getLogger(__name__)


class GenericTask(Task):
    estimators = {
        "xgboost": XGBoostSklearnEstimator,
        "xgb_limitdepth": XGBoostLimitDepthEstimator,
        "rf": RandomForestEstimator,
        "lgbm": LGBMEstimator,
        "lrl1": LRL1Classifier,
        "lrl2": LRL2Classifier,
        "catboost": CatBoostEstimator,
        "extra_tree": ExtraTreesEstimator,
        "kneighbor": KNeighborsEstimator,
        "transformer": TransformersEstimator,
        "transformer_ms": TransformersEstimatorModelSelection,
    }

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
        if X_train_all is not None and y_train_all is not None:
            assert (
                isinstance(X_train_all, np.ndarray)
                or issparse(X_train_all)
                or isinstance(X_train_all, pd.DataFrame)
            ), (
                "X_train_all must be a numpy array, a pandas dataframe, "
                "or Scipy sparse matrix."
            )
            assert isinstance(y_train_all, np.ndarray) or isinstance(
                y_train_all, pd.Series
            ), "y_train_all must be a numpy array or a pandas series."
            assert (
                X_train_all.size != 0 and y_train_all.size != 0
            ), "Input data must not be empty."
            if isinstance(X_train_all, np.ndarray) and len(X_train_all.shape) == 1:
                X_train_all = np.reshape(X_train_all, (X_train_all.size, 1))
            if isinstance(y_train_all, np.ndarray):
                y_train_all = y_train_all.flatten()
            assert (
                X_train_all.shape[0] == y_train_all.shape[0]
            ), "# rows in X_train must match length of y_train."
            automl._df = isinstance(X_train_all, pd.DataFrame)
            automl._nrow, automl._ndim = X_train_all.shape
            if self.is_ts_forecast():
                X_train_all = pd.DataFrame(X_train_all)
                X_train_all, y_train_all = self._validate_ts_data(
                    X_train_all, y_train_all
                )
            X, y = X_train_all, y_train_all
        elif dataframe is not None and label is not None:
            assert isinstance(
                dataframe, pd.DataFrame
            ), "dataframe must be a pandas DataFrame"
            assert label in dataframe.columns, "label must a column name in dataframe"
            automl._df = True
            if self.is_ts_forecast():
                dataframe = self._validate_ts_data(dataframe)
            X = dataframe.drop(columns=label)
            automl._nrow, automl._ndim = X.shape
            y = dataframe[label]
        else:
            raise ValueError("either X_train+y_train or dataframe+label are required")

        # check the validity of input dimensions for NLP tasks, so need to check _is_nlp_task not estimator
        if self.is_nlp():
            from flaml.automl.nlp.utils import is_a_list_of_str

            is_all_str = True
            is_all_list = True
            for column in X.columns:
                assert X[column].dtype.name in (
                    "object",
                    "string",
                ), "If the task is an NLP task, X can only contain text columns"
                for each_cell in X[column]:
                    if each_cell is not None:
                        is_str = isinstance(each_cell, str)
                        is_list_of_int = isinstance(each_cell, list) and all(
                            isinstance(x, int) for x in each_cell
                        )
                        is_list_of_str = is_a_list_of_str(each_cell)
                        if self.is_token_classification():
                            assert is_list_of_str, (
                                "For the token-classification task, the input column needs to be a list of string,"
                                "instead of string, e.g., ['EU', 'rejects','German', 'call','to','boycott','British','lamb','.',].",
                                "For more examples, please refer to test/nlp/test_autohf_tokenclassification.py",
                            )
                        else:
                            assert is_str or is_list_of_int, (
                                "Each column of the input must either be str (untokenized) "
                                "or a list of integers (tokenized)"
                            )
                        is_all_str &= is_str
                        is_all_list &= is_list_of_int or is_list_of_str
            assert is_all_str or is_all_list, (
                "Currently FLAML only supports two modes for NLP: either all columns of X are string (non-tokenized), "
                "or all columns of X are integer ids (tokenized)"
            )

        if issparse(X_train_all) or automl._skip_transform:
            automl._transformer = automl._label_transformer = False
            automl._X_train_all, automl._y_train_all = X, y
        else:
            from flaml.automl.data import DataTransformer

            automl._transformer = DataTransformer()

            (
                automl._X_train_all,
                automl._y_train_all,
            ) = automl._transformer.fit_transform(X, y, self)
            automl._label_transformer = automl._transformer.label_transformer
            if self.is_token_classification():
                if hasattr(automl._label_transformer, "label_list"):
                    state.fit_kwargs.update(
                        {"label_list": automl._label_transformer.label_list}
                    )
                elif "label_list" not in state.fit_kwargs:
                    for each_fit_kwargs in state.fit_kwargs_by_estimator.values():
                        assert (
                            "label_list" in each_fit_kwargs
                        ), "For the token-classification task, you must either (1) pass token labels; or (2) pass id labels and the label list. "
                        "Please refer to the documentation for more details: https://microsoft.github.io/FLAML/docs/Examples/AutoML-NLP#a-simple-token-classification-example"
            automl._feature_names_in_ = (
                automl._X_train_all.columns.to_list()
                if hasattr(automl._X_train_all, "columns")
                else None
            )

        automl._sample_weight_full = state.fit_kwargs.get(
            "sample_weight"
        )  # NOTE: _validate_data is before kwargs is updated to fit_kwargs_by_estimator
        if X_val is not None and y_val is not None:
            assert (
                isinstance(X_val, np.ndarray)
                or issparse(X_val)
                or isinstance(X_val, pd.DataFrame)
            ), (
                "X_val must be None, a numpy array, a pandas dataframe, "
                "or Scipy sparse matrix."
            )
            assert isinstance(y_val, np.ndarray) or isinstance(
                y_val, pd.Series
            ), "y_val must be None, a numpy array or a pandas series."
            assert X_val.size != 0 and y_val.size != 0, (
                "Validation data are expected to be nonempty. "
                "Use None for X_val and y_val if no validation data."
            )
            if isinstance(y_val, np.ndarray):
                y_val = y_val.flatten()
            assert (
                X_val.shape[0] == y_val.shape[0]
            ), "# rows in X_val must match length of y_val."
            if automl._transformer:
                state.X_val = automl._transformer.transform(X_val)
            else:
                state.X_val = X_val
            # If it's NLG_TASKS, y_val is a pandas series containing the output sequence tokens,
            # so we cannot use label_transformer.transform to process it
            if automl._label_transformer:
                state.y_val = automl._label_transformer.transform(y_val)
            else:
                state.y_val = y_val
        else:
            state.X_val = state.y_val = None

        if groups is not None and len(groups) != automl._nrow:
            # groups is given as group counts
            state.groups = np.concatenate([[i] * c for i, c in enumerate(groups)])
            assert (
                len(state.groups) == automl._nrow
            ), "the sum of group counts must match the number of examples"
            state.groups_val = (
                np.concatenate([[i] * c for i, c in enumerate(groups_val)])
                if groups_val is not None
                else None
            )
        else:
            state.groups_val = groups_val
            state.groups = groups

    @staticmethod
    def _validate_ts_data(
        dataframe,
        y_train_all=None,
    ):
        assert (
            dataframe[dataframe.columns[0]].dtype.name == "datetime64[ns]"
        ), f"For '{TS_FORECAST}' task, the first column must contain timestamp values."
        if y_train_all is not None:
            y_df = (
                pd.DataFrame(y_train_all)
                if isinstance(y_train_all, pd.Series)
                else pd.DataFrame(y_train_all, columns=["labels"])
            )
            dataframe = dataframe.join(y_df)
        duplicates = dataframe.duplicated()
        if any(duplicates):
            logger.warning(
                "Duplicate timestamp values found in timestamp column. "
                f"\n{dataframe.loc[duplicates, dataframe][dataframe.columns[0]]}"
            )
            dataframe = dataframe.drop_duplicates()
            logger.warning("Removed duplicate rows based on all columns")
            assert (
                dataframe[[dataframe.columns[0]]].duplicated() is None
            ), "Duplicate timestamp values with different values for other columns."
        ts_series = pd.to_datetime(dataframe[dataframe.columns[0]])
        inferred_freq = pd.infer_freq(ts_series)
        if inferred_freq is None:
            logger.warning(
                "Missing timestamps detected. To avoid error with estimators, set estimator list to ['prophet']. "
            )
        if y_train_all is not None:
            return dataframe.iloc[:, :-1], dataframe.iloc[:, -1]
        return dataframe

    def prepare_data(
        self,
        state,
        X_train_all,
        y_train_all,
        auto_augment,
        eval_method,
        split_type,
        split_ratio,
        n_splits,
        data_is_df,
        sample_weight_full,
    ) -> int:
        X_val, y_val = state.X_val, state.y_val
        if issparse(X_val):
            X_val = X_val.tocsr()
        if issparse(X_train_all):
            X_train_all = X_train_all.tocsr()
        if (
            self.is_classification()
            and auto_augment
            and state.fit_kwargs.get("sample_weight")
            is None  # NOTE: _prepare_data is before kwargs is updated to fit_kwargs_by_estimator
            and split_type in ["stratified", "uniform"]
            and not self.is_token_classification()
        ):
            # logger.info(f"label {pd.unique(y_train_all)}")
            label_set, counts = np.unique(y_train_all, return_counts=True)
            # augment rare classes
            rare_threshld = 20
            rare = counts < rare_threshld
            rare_label, rare_counts = label_set[rare], counts[rare]
            for i, label in enumerate(rare_label):
                count = rare_count = rare_counts[i]
                rare_index = y_train_all == label
                n = len(y_train_all)
                while count < rare_threshld:
                    if data_is_df:
                        X_train_all = concat(
                            X_train_all, X_train_all.iloc[:n].loc[rare_index]
                        )
                    else:
                        X_train_all = concat(
                            X_train_all, X_train_all[:n][rare_index, :]
                        )
                    if isinstance(y_train_all, pd.Series):
                        y_train_all = concat(
                            y_train_all, y_train_all.iloc[:n].loc[rare_index]
                        )
                    else:
                        y_train_all = np.concatenate(
                            [y_train_all, y_train_all[:n][rare_index]]
                        )
                    count += rare_count
                logger.info(f"class {label} augmented from {rare_count} to {count}")
        SHUFFLE_SPLIT_TYPES = ["uniform", "stratified"]
        if split_type in SHUFFLE_SPLIT_TYPES:
            if sample_weight_full is not None:
                X_train_all, y_train_all, state.sample_weight_all = shuffle(
                    X_train_all,
                    y_train_all,
                    sample_weight_full,
                    random_state=RANDOM_SEED,
                )
                state.fit_kwargs[
                    "sample_weight"
                ] = (
                    state.sample_weight_all
                )  # NOTE: _prepare_data is before kwargs is updated to fit_kwargs_by_estimator
                if isinstance(state.sample_weight_all, pd.Series):
                    state.sample_weight_all.reset_index(drop=True, inplace=True)
            else:
                X_train_all, y_train_all = shuffle(
                    X_train_all, y_train_all, random_state=RANDOM_SEED
                )
            if data_is_df:
                X_train_all.reset_index(drop=True, inplace=True)
            if isinstance(y_train_all, pd.Series):
                y_train_all.reset_index(drop=True, inplace=True)

        X_train, y_train = X_train_all, y_train_all
        state.groups_all = state.groups
        if X_val is None and eval_method == "holdout":
            # if eval_method = holdout, make holdout data
            if split_type == "time":
                if self.is_ts_forecast():
                    period = state.fit_kwargs[
                        "period"
                    ]  # NOTE: _prepare_data is before kwargs is updated to fit_kwargs_by_estimator
                    if self.is_ts_forecastpanel():
                        X_train_all["time_idx"] -= X_train_all["time_idx"].min()
                        X_train_all["time_idx"] = X_train_all["time_idx"].astype("int")
                        ids = state.fit_kwargs["group_ids"].copy()
                        ids.append(TS_TIMESTAMP_COL)
                        ids.append("time_idx")
                        y_train_all = pd.DataFrame(y_train_all)
                        y_train_all[ids] = X_train_all[ids]
                        X_train_all = X_train_all.sort_values(ids)
                        y_train_all = y_train_all.sort_values(ids)
                        training_cutoff = X_train_all["time_idx"].max() - period
                        X_train = X_train_all[lambda x: x.time_idx <= training_cutoff]
                        y_train = y_train_all[
                            lambda x: x.time_idx <= training_cutoff
                        ].drop(columns=ids)
                        X_val = X_train_all[lambda x: x.time_idx > training_cutoff]
                        y_val = y_train_all[
                            lambda x: x.time_idx > training_cutoff
                        ].drop(columns=ids)
                    else:
                        num_samples = X_train_all.shape[0]
                        assert (
                            period < num_samples
                        ), f"period={period}>#examples={num_samples}"
                        split_idx = num_samples - period
                        X_train = X_train_all[:split_idx]
                        y_train = y_train_all[:split_idx]
                        X_val = X_train_all[split_idx:]
                        y_val = y_train_all[split_idx:]
                else:
                    if (
                        "sample_weight" in state.fit_kwargs
                    ):  # NOTE: _prepare_data is before kwargs is updated to fit_kwargs_by_estimator
                        (
                            X_train,
                            X_val,
                            y_train,
                            y_val,
                            state.fit_kwargs[
                                "sample_weight"
                            ],  # NOTE: _prepare_data is before kwargs is updated to fit_kwargs_by_estimator
                            state.weight_val,
                        ) = train_test_split(
                            X_train_all,
                            y_train_all,
                            state.fit_kwargs[
                                "sample_weight"
                            ],  # NOTE: _prepare_data is before kwargs is updated to fit_kwargs_by_estimator
                            test_size=split_ratio,
                            shuffle=False,
                        )
                    else:
                        X_train, X_val, y_train, y_val = train_test_split(
                            X_train_all,
                            y_train_all,
                            test_size=split_ratio,
                            shuffle=False,
                        )
            elif split_type == "group":
                gss = GroupShuffleSplit(
                    n_splits=1, test_size=split_ratio, random_state=RANDOM_SEED
                )
                for train_idx, val_idx in gss.split(
                    X_train_all, y_train_all, state.groups_all
                ):
                    if data_is_df:
                        X_train = X_train_all.iloc[train_idx]
                        X_val = X_train_all.iloc[val_idx]
                    else:
                        X_train, X_val = X_train_all[train_idx], X_train_all[val_idx]
                    y_train, y_val = y_train_all[train_idx], y_train_all[val_idx]
                    state.groups = state.groups_all[train_idx]
                    state.groups_val = state.groups_all[val_idx]
            elif self.is_classification():
                # for classification, make sure the labels are complete in both
                # training and validation data
                label_set, first = np.unique(y_train_all, return_index=True)
                rest = []
                last = 0
                first.sort()
                for i in range(len(first)):
                    rest.extend(range(last, first[i]))
                    last = first[i] + 1
                rest.extend(range(last, len(y_train_all)))
                X_first = X_train_all.iloc[first] if data_is_df else X_train_all[first]
                X_rest = X_train_all.iloc[rest] if data_is_df else X_train_all[rest]
                y_rest = y_train_all[rest]
                stratify = y_rest if split_type == "stratified" else None
                if (
                    "sample_weight" in state.fit_kwargs
                ):  # NOTE: _prepare_data is before kwargs is updated to fit_kwargs_by_estimator
                    (
                        X_train,
                        X_val,
                        y_train,
                        y_val,
                        weight_train,
                        weight_val,
                    ) = train_test_split(
                        X_rest,
                        y_rest,
                        state.fit_kwargs["sample_weight"][
                            rest
                        ],  # NOTE: _prepare_data is before kwargs is updated to fit_kwargs_by_estimator
                        test_size=split_ratio,
                        stratify=stratify,
                        random_state=RANDOM_SEED,
                    )
                    weight1 = state.fit_kwargs["sample_weight"][
                        first
                    ]  # NOTE: _prepare_data is before kwargs is updated to fit_kwargs_by_estimator
                    state.weight_val = concat(weight1, weight_val)
                    state.fit_kwargs[
                        "sample_weight"
                    ] = concat(  # NOTE: _prepare_data is before kwargs is updated to fit_kwargs_by_estimator
                        weight1, weight_train
                    )
                else:
                    X_train, X_val, y_train, y_val = train_test_split(
                        X_rest,
                        y_rest,
                        test_size=split_ratio,
                        stratify=stratify,
                        random_state=RANDOM_SEED,
                    )
                X_train = concat(X_first, X_train)
                y_train = (
                    concat(label_set, y_train)
                    if data_is_df
                    else np.concatenate([label_set, y_train])
                )
                X_val = concat(X_first, X_val)
                y_val = (
                    concat(label_set, y_val)
                    if data_is_df
                    else np.concatenate([label_set, y_val])
                )
            elif self.is_regression():
                if (
                    "sample_weight" in state.fit_kwargs
                ):  # NOTE: _prepare_data is before kwargs is updated to fit_kwargs_by_estimator
                    (
                        X_train,
                        X_val,
                        y_train,
                        y_val,
                        state.fit_kwargs[
                            "sample_weight"
                        ],  # NOTE: _prepare_data is before kwargs is updated to fit_kwargs_by_estimator
                        state.weight_val,
                    ) = train_test_split(
                        X_train_all,
                        y_train_all,
                        state.fit_kwargs[
                            "sample_weight"
                        ],  # NOTE: _prepare_data is before kwargs is updated to fit_kwargs_by_estimator
                        test_size=split_ratio,
                        random_state=RANDOM_SEED,
                    )
                else:
                    X_train, X_val, y_train, y_val = train_test_split(
                        X_train_all,
                        y_train_all,
                        test_size=split_ratio,
                        random_state=RANDOM_SEED,
                    )
        state.data_size = X_train.shape
        state.X_train, state.y_train = X_train, y_train
        state.X_val, state.y_val = X_val, y_val
        state.X_train_all = X_train_all
        state.y_train_all = y_train_all
        if eval_method == "holdout":
            state.kf = None
            return
        if split_type == "group":
            # logger.info("Using GroupKFold")
            assert (
                len(state.groups_all) == y_train_all.size
            ), "the length of groups must match the number of examples"
            assert (
                len(np.unique(state.groups_all)) >= n_splits
            ), "the number of groups must be equal or larger than n_splits"
            state.kf = GroupKFold(n_splits)
        elif split_type == "stratified":
            # logger.info("Using StratifiedKFold")
            assert y_train_all.size >= n_splits, (
                f"{n_splits}-fold cross validation"
                f" requires input data with at least {n_splits} examples."
            )
            assert y_train_all.size >= 2 * n_splits, (
                f"{n_splits}-fold cross validation with metric=r2 "
                f"requires input data with at least {n_splits*2} examples."
            )
            state.kf = RepeatedStratifiedKFold(
                n_splits=n_splits, n_repeats=1, random_state=RANDOM_SEED
            )
        elif split_type == "time":
            # logger.info("Using TimeSeriesSplit")
            if self.is_ts_forecast() and not self.is_ts_forecastpanel():
                period = state.fit_kwargs[
                    "period"
                ]  # NOTE: _prepare_data is before kwargs is updated to fit_kwargs_by_estimator
                if period * (n_splits + 1) > y_train_all.size:
                    n_splits = int(y_train_all.size / period - 1)
                    assert n_splits >= 2, (
                        f"cross validation for forecasting period={period}"
                        f" requires input data with at least {3 * period} examples."
                    )
                    logger.info(f"Using nsplits={n_splits} due to data size limit.")
                state.kf = TimeSeriesSplit(n_splits=n_splits, test_size=period)
            elif self.is_ts_forecastpanel():
                n_groups = X_train.groupby(state.fit_kwargs.get("group_ids")).ngroups
                period = state.fit_kwargs.get("period")
                state.kf = TimeSeriesSplit(
                    n_splits=n_splits, test_size=period * n_groups
                )
            else:
                state.kf = TimeSeriesSplit(n_splits=n_splits)
        elif isinstance(split_type, str):
            # logger.info("Using RepeatedKFold")
            state.kf = RepeatedKFold(
                n_splits=n_splits, n_repeats=1, random_state=RANDOM_SEED
            )
        else:
            # logger.info("Using splitter object")
            state.kf = split_type
        if isinstance(state.kf, (GroupKFold, StratifiedGroupKFold)):
            # self._split_type is either "group", a GroupKFold object, or a StratifiedGroupKFold object
            state.kf.groups = state.groups_all

    def decide_split_type(
        self,
        split_type,
        y_train_all,
        fit_kwargs,
        groups=None,
    ) -> str:
        if self.name == "classification":
            self.name = get_classification_objective(len(np.unique(y_train_all)))
        if not isinstance(split_type, str):
            assert hasattr(split_type, "split") and hasattr(
                split_type, "get_n_splits"
            ), "split_type must be a string or a splitter object with split and get_n_splits methods."
            assert (
                not isinstance(split_type, GroupKFold) or groups is not None
            ), "GroupKFold requires groups to be provided."
            return split_type

        elif self.is_ts_forecast():
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

        elif self.is_classification():
            assert split_type in ["auto", "stratified", "uniform", "time", "group"]
            return (
                split_type
                if split_type != "auto"
                else groups is None and "stratified" or "group"
            )

        elif self.is_regression():
            assert split_type in ["auto", "uniform", "time", "group"]
            return split_type if split_type != "auto" else "uniform"

        elif self.is_rank():
            assert groups is not None, "groups must be specified for ranking task."
            assert split_type in ["auto", "group"]
            return "group"

        elif self.is_nlg():
            assert split_type in ["auto", "uniform", "time", "group"]
            return split_type if split_type != "auto" else "uniform"

    def preprocess(self, X, transformer=None):
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
                raise IndexError(
                    "Test data contains more columns than training data, exiting"
                )
        elif isinstance(X, int):
            return X
        elif issparse(X):
            X = X.tocsr()
        if self.is_ts_forecast():
            X = pd.DataFrame(X)
        if transformer:
            X = transformer.transform(X)
        return X

    def evaluate_model_CV(
        self,
        config: dict,
        estimator: EstimatorSubclass,
        X_train_all,
        y_train_all,
        budget,
        kf,
        eval_metric,
        best_val_loss,
        cv_score_agg_func=None,
        log_training_metric=False,
        fit_kwargs: Optional[dict] = None,
        free_mem_ratio=0,
    ):
        if fit_kwargs is None:
            fit_kwargs = {}
        if cv_score_agg_func is None:
            cv_score_agg_func = default_cv_score_agg_func
        start_time = time.time()
        val_loss_folds = []
        log_metric_folds = []
        metric = None
        train_time = pred_time = 0
        total_fold_num = 0
        n = kf.get_n_splits()
        X_train_split, y_train_split = X_train_all, y_train_all
        if self.is_classification():
            labels = np.unique(y_train_all)
        else:
            labels = fit_kwargs.get(
                "label_list"
            )  # pass the label list on to compute the evaluation metric
        groups = None
        shuffle = getattr(kf, "shuffle", not self.is_ts_forecast())
        if isinstance(kf, RepeatedStratifiedKFold):
            kf = kf.split(X_train_split, y_train_split)
        elif isinstance(kf, (GroupKFold, StratifiedGroupKFold)):
            groups = kf.groups
            kf = kf.split(X_train_split, y_train_split, groups)
            shuffle = False
        elif isinstance(kf, TimeSeriesSplit):
            kf = kf.split(X_train_split, y_train_split)
        else:
            kf = kf.split(X_train_split)
        rng = np.random.RandomState(2020)
        budget_per_train = budget and budget / n
        if "sample_weight" in fit_kwargs:
            weight = fit_kwargs["sample_weight"]
            weight_val = None
        else:
            weight = weight_val = None
        for train_index, val_index in kf:
            if shuffle:
                train_index = rng.permutation(train_index)
            if isinstance(X_train_all, pd.DataFrame):
                X_train = X_train_split.iloc[train_index]
                X_val = X_train_split.iloc[val_index]
            else:
                X_train, X_val = X_train_split[train_index], X_train_split[val_index]
            y_train, y_val = y_train_split[train_index], y_train_split[val_index]
            estimator.cleanup()
            if weight is not None:
                fit_kwargs["sample_weight"], weight_val = (
                    weight[train_index],
                    weight[val_index],
                )
            if groups is not None:
                fit_kwargs["groups"] = (
                    groups[train_index]
                    if isinstance(groups, np.ndarray)
                    else groups.iloc[train_index]
                )
                groups_val = (
                    groups[val_index]
                    if isinstance(groups, np.ndarray)
                    else groups.iloc[val_index]
                )
            else:
                groups_val = None
            val_loss_i, metric_i, train_time_i, pred_time_i = get_val_loss(
                config,
                estimator,
                X_train,
                y_train,
                X_val,
                y_val,
                weight_val,
                groups_val,
                eval_metric,
                self,
                labels,
                budget_per_train,
                log_training_metric=log_training_metric,
                fit_kwargs=fit_kwargs,
                free_mem_ratio=free_mem_ratio,
            )
            if isinstance(metric_i, dict) and "intermediate_results" in metric_i.keys():
                del metric_i["intermediate_results"]
            if weight is not None:
                fit_kwargs["sample_weight"] = weight
            total_fold_num += 1
            val_loss_folds.append(val_loss_i)
            log_metric_folds.append(metric_i)
            train_time += train_time_i
            pred_time += pred_time_i
            if budget and time.time() - start_time >= budget:
                break
        val_loss, metric = cv_score_agg_func(val_loss_folds, log_metric_folds)
        n = total_fold_num
        pred_time /= n
        return val_loss, metric, train_time, pred_time

    def default_estimator_list(self, estimator_list: List[str]) -> List[str]:
        if "auto" != estimator_list:
            return estimator_list
        if self.is_rank():
            estimator_list = ["lgbm", "xgboost", "xgb_limitdepth"]
        elif self.is_nlp():
            estimator_list = ["transformer"]
        elif self.is_ts_forecastpanel():
            estimator_list = ["tft"]
        else:
            try:
                import catboost

                estimator_list = [
                    "lgbm",
                    "rf",
                    "catboost",
                    "xgboost",
                    "extra_tree",
                    "xgb_limitdepth",
                ]
            except ImportError:
                estimator_list = [
                    "lgbm",
                    "rf",
                    "xgboost",
                    "extra_tree",
                    "xgb_limitdepth",
                ]
            if self.is_ts_forecast():
                # catboost is removed because it has a `name` parameter, making it incompatible with hcrystalball
                if "catboost" in estimator_list:
                    estimator_list.remove("catboost")
                if self.is_ts_forecastregression():
                    try:
                        import prophet

                        estimator_list += ["prophet", "arima", "sarimax"]
                    except ImportError:
                        estimator_list += ["arima", "sarimax"]
            elif not self.is_regression():
                estimator_list += ["lrl1"]

        return estimator_list

    def default_metric(self, metric: str) -> str:
        if "auto" != metric:
            return metric

        if self.is_nlp():
            from flaml.automl.nlp.utils import (
                load_default_huggingface_metric_for_task,
            )

            return load_default_huggingface_metric_for_task(self.name)
        elif self.is_binary():
            return "roc_auc"
        elif self.is_multiclass():
            return "log_loss"
        elif self.is_ts_forecast():
            return "mape"
        elif self.is_rank():
            return "ndcg"
        else:
            return "r2"
