# !
#  * Copyright (c) FLAML authors. All rights reserved.
#  * Licensed under the MIT License. See LICENSE file in the
#  * project root for license information.
from contextlib import contextmanager
from functools import partial
import signal
import os
from typing import Callable, List, Union
import numpy as np
import time
import logging
import shutil
import sys
import math
from flaml import tune
from flaml.automl.data import (
    group_counts,
)
from flaml.automl.task.task import (
    Task,
    SEQCLASSIFICATION,
    SEQREGRESSION,
    TOKENCLASSIFICATION,
    SUMMARIZATION,
    NLG_TASKS,
)
from flaml.automl.task.factory import task_factory

try:
    from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
    from sklearn.ensemble import ExtraTreesRegressor, ExtraTreesClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.dummy import DummyClassifier, DummyRegressor
except ImportError:
    pass

try:
    from scipy.sparse import issparse
except ImportError:
    pass

from flaml.automl.spark import psDataFrame, sparkDataFrame, psSeries, ERROR as SPARK_ERROR, DataFrame, Series
from flaml.automl.spark.utils import len_labels, to_pandas_on_spark
from flaml.automl.spark.configs import (
    ParamList_LightGBM_Classifier,
    ParamList_LightGBM_Regressor,
    ParamList_LightGBM_Ranker,
)

if DataFrame is not None:
    from pandas import to_datetime

try:
    import psutil
except ImportError:
    psutil = None
try:
    import resource
except ImportError:
    resource = None

try:
    from lightgbm import LGBMClassifier, LGBMRegressor, LGBMRanker
except ImportError:
    LGBMClassifier = LGBMRegressor = LGBMRanker = None

logger = logging.getLogger("flaml.automl")
# FREE_MEM_RATIO = 0.2


def TimeoutHandler(sig, frame):
    raise TimeoutError(sig, frame)


@contextmanager
def limit_resource(memory_limit, time_limit):
    if memory_limit > 0:
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        if soft < 0 and (hard < 0 or memory_limit <= hard) or memory_limit < soft:
            try:
                resource.setrlimit(resource.RLIMIT_AS, (int(memory_limit), hard))
            except ValueError:
                # According to https://bugs.python.org/issue40518, it's a mac-specific error.
                pass
    main_thread = False
    if time_limit is not None:
        try:
            signal.signal(signal.SIGALRM, TimeoutHandler)
            signal.alarm(int(time_limit) or 1)
            main_thread = True
        except ValueError:
            pass
    try:
        yield
    finally:
        if main_thread:
            signal.alarm(0)
        if memory_limit > 0:
            resource.setrlimit(resource.RLIMIT_AS, (soft, hard))


class BaseEstimator:
    """The abstract class for all learners.

    Typical examples:
    * XGBoostEstimator: for regression.
    * XGBoostSklearnEstimator: for classification.
    * LGBMEstimator, RandomForestEstimator, LRL1Classifier, LRL2Classifier:
        for both regression and classification.
    """

    def __init__(self, task="binary", **config):
        """Constructor.

        Args:
            task: A string of the task type, one of
                'binary', 'multiclass', 'regression', 'rank', 'seq-classification',
                'seq-regression', 'token-classification', 'multichoice-classification',
                'summarization', 'ts_forecast', 'ts_forecast_classification'.
            config: A dictionary containing the hyperparameter names, 'n_jobs' as keys.
                n_jobs is the number of parallel threads.
        """
        self._task = task if isinstance(task, Task) else task_factory(task, None, None)
        self.params = self.config2params(config)
        self.estimator_class = self._model = None
        if "_estimator_type" in config:
            self._estimator_type = self.params.pop("_estimator_type")
        else:
            self._estimator_type = "classifier" if self._task.is_classification() else "regressor"

    def get_params(self, deep=False):
        params = self.params.copy()
        params["task"] = self._task
        if hasattr(self, "_estimator_type"):
            params["_estimator_type"] = self._estimator_type
        return params

    @property
    def classes_(self):
        return self._model.classes_

    @property
    def n_features_in_(self):
        return self._model.n_features_in_

    @property
    def model(self):
        """Trained model after fit() is called, or None before fit() is called."""
        return self._model

    @property
    def estimator(self):
        """Trained model after fit() is called, or None before fit() is called."""
        return self._model

    @property
    def feature_names_in_(self):
        """
        if self._model has attribute feature_names_in_, return it.
        otherwise, if self._model has attribute feature_name_, return it.
        otherwise, if self._model has attribute feature_names, return it.
        otherwise, if self._model has method get_booster, return the feature names.
        otherwise, return None.
        """
        if hasattr(self._model, "feature_names_in_"):  # for sklearn, xgboost>=1.6
            return self._model.feature_names_in_
        if hasattr(self._model, "feature_name_"):  # for lightgbm
            return self._model.feature_name_
        if hasattr(self._model, "feature_names"):  # for XGBoostEstimator
            return self._model.feature_names
        if hasattr(self._model, "get_booster"):
            # get feature names for xgboost<1.6
            # https://xgboost.readthedocs.io/en/latest/python/python_api.html#xgboost.Booster.feature_names
            booster = self._model.get_booster()
            return booster.feature_names
        return None

    @property
    def feature_importances_(self):
        """
        if self._model has attribute feature_importances_, return it.
        otherwise, if self._model has attribute coef_, return it.
        otherwise, return None.
        """
        if hasattr(self._model, "feature_importances_"):
            # for sklearn, lightgbm, catboost, xgboost
            return self._model.feature_importances_
        elif hasattr(self._model, "coef_"):  # for linear models
            return self._model.coef_
        else:
            return None

    def _preprocess(self, X):
        return X

    def _fit(self, X_train, y_train, **kwargs):
        current_time = time.time()
        if "groups" in kwargs:
            kwargs = kwargs.copy()
            groups = kwargs.pop("groups")
            if self._task == "rank":
                kwargs["group"] = group_counts(groups)
                # groups_val = kwargs.get('groups_val')
                # if groups_val is not None:
                #     kwargs['eval_group'] = [group_counts(groups_val)]
                #     kwargs['eval_set'] = [
                #         (kwargs['X_val'], kwargs['y_val'])]
                #     kwargs['verbose'] = False
                #     del kwargs['groups_val'], kwargs['X_val'], kwargs['y_val']
        X_train = self._preprocess(X_train)
        model = self.estimator_class(**self.params)
        if logger.level == logging.DEBUG:
            # xgboost 1.6 doesn't display all the params in the model str
            logger.debug(f"flaml.model - {model} fit started with params {self.params}")
        model.fit(X_train, y_train, **kwargs)
        if logger.level == logging.DEBUG:
            logger.debug(f"flaml.model - {model} fit finished")
        train_time = time.time() - current_time
        self._model = model
        return train_time

    def fit(self, X_train, y_train, budget=None, free_mem_ratio=0, **kwargs):
        """Train the model from given training data.

        Args:
            X_train: A numpy array or a dataframe of training data in shape n*m.
            y_train: A numpy array or a series of labels in shape n*1.
            budget: A float of the time budget in seconds.
            free_mem_ratio: A float between 0 and 1 for the free memory ratio to keep during training.

        Returns:
            train_time: A float of the training time in seconds.
        """
        if (
            getattr(self, "limit_resource", None)
            and resource is not None
            and (budget is not None or psutil is not None)
        ):
            start_time = time.time()
            mem = psutil.virtual_memory() if psutil is not None else None
            try:
                with limit_resource(
                    mem.available * (1 - free_mem_ratio) + psutil.Process(os.getpid()).memory_info().rss
                    if mem is not None
                    else -1,
                    budget,
                ):
                    train_time = self._fit(X_train, y_train, **kwargs)
            except (MemoryError, TimeoutError) as e:
                logger.warning(f"{e.__class__} {e}")
                if self._task.is_classification():
                    model = DummyClassifier()
                else:
                    model = DummyRegressor()
                X_train = self._preprocess(X_train)
                model.fit(X_train, y_train)
                self._model = model
                train_time = time.time() - start_time
        else:
            train_time = self._fit(X_train, y_train, **kwargs)
        return train_time

    def predict(self, X, **kwargs):
        """Predict label from features.

        Args:
            X: A numpy array or a dataframe of featurized instances, shape n*m.

        Returns:
            A numpy array of shape n*1.
            Each element is the label for a instance.
        """
        if self._model is not None:
            X = self._preprocess(X)
            return self._model.predict(X, **kwargs)
        else:
            logger.warning("Estimator is not fit yet. Please run fit() before predict().")
            return np.ones(X.shape[0])

    def predict_proba(self, X, **kwargs):
        """Predict the probability of each class from features.

        Only works for classification problems

        Args:
            X: A numpy array of featurized instances, shape n*m.

        Returns:
            A numpy array of shape n*c. c is the # classes.
            Each element at (i,j) is the probability for instance i to be in
                class j.
        """
        assert self._task.is_classification(), "predict_proba() only for classification."

        X = self._preprocess(X)
        return self._model.predict_proba(X, **kwargs)

    def score(self, X_val: DataFrame, y_val: Series, **kwargs):
        """Report the evaluation score of a trained estimator.


        Args:
            X_val: A pandas dataframe of the validation input data.
            y_val: A pandas series of the validation label.
            kwargs: keyword argument of the evaluation function, for example:
                - metric: A string of the metric name or a function
                e.g., 'accuracy', 'roc_auc', 'roc_auc_ovr', 'roc_auc_ovo',
                'f1', 'micro_f1', 'macro_f1', 'log_loss', 'mae', 'mse', 'r2',
                'mape'. Default is 'auto'.
                If metric is given, the score will report the user specified metric.
                If metric is not given, the metric is set to accuracy for classification and r2
                for regression.
                You can also pass a customized metric function, for examples on how to pass a
                customized metric function, please check
                [test/nlp/test_autohf_custom_metric.py](https://github.com/microsoft/FLAML/blob/main/test/nlp/test_autohf_custom_metric.py) and
                [test/automl/test_multiclass.py](https://github.com/microsoft/FLAML/blob/main/test/automl/test_multiclass.py).

        Returns:
            The evaluation score on the validation dataset.
        """
        from .ml import metric_loss_score
        from .ml import is_min_metric

        if self._model is not None:
            if self._task == "rank":
                raise NotImplementedError("AutoML.score() is not implemented for ranking")
            else:
                X_val = self._preprocess(X_val)
                metric = kwargs.pop("metric", None)
                if metric:
                    y_pred = self.predict(X_val, **kwargs)
                    if is_min_metric(metric):
                        return metric_loss_score(metric, y_pred, y_val)
                    else:
                        return 1.0 - metric_loss_score(metric, y_pred, y_val)
                else:
                    return self._model.score(X_val, y_val, **kwargs)
        else:
            logger.warning("Estimator is not fit yet. Please run fit() before predict().")
            return 0.0

    def cleanup(self):
        del self._model
        self._model = None

    @classmethod
    def search_space(cls, data_size, task, **params):
        """[required method] search space.

        Args:
            data_size: A tuple of two integers, number of rows and columns.
            task: A str of the task type, e.g., "binary", "multiclass", "regression".

        Returns:
            A dictionary of the search space.
            Each key is the name of a hyperparameter, and value is a dict with
                its domain (required) and low_cost_init_value, init_value,
                cat_hp_cost (if applicable).
                e.g., ```{'domain': tune.randint(lower=1, upper=10), 'init_value': 1}```.
        """
        return {}

    @classmethod
    def size(cls, config: dict) -> float:
        """[optional method] memory size of the estimator in bytes.

        Args:
            config: A dict of the hyperparameter config.

        Returns:
            A float of the memory size required by the estimator to train the
            given config.
        """
        return 1.0

    @classmethod
    def cost_relative2lgbm(cls) -> float:
        """[optional method] relative cost compared to lightgbm."""
        return 1.0

    @classmethod
    def init(cls):
        """[optional method] initialize the class."""
        pass

    def config2params(self, config: dict) -> dict:
        """[optional method] config dict to params dict

        Args:
            config: A dict of the hyperparameter config.

        Returns:
            A dict that will be passed to self.estimator_class's constructor.
        """
        params = config.copy()
        if "FLAML_sample_size" in params:
            params.pop("FLAML_sample_size")
        return params


class SparkEstimator(BaseEstimator):
    """The base class for fine-tuning spark models, using pyspark.ml and SynapseML API."""

    def __init__(self, task="binary", **config):
        if SPARK_ERROR:
            raise SPARK_ERROR
        super().__init__(task, **config)
        self.df_train = None

    def _preprocess(
        self,
        X_train: Union[psDataFrame, sparkDataFrame],
        y_train: psSeries = None,
        index_col: str = "tmp_index_col",
        return_label: bool = False,
    ):
        # TODO: optimize this, support pyspark.sql.DataFrame
        if y_train is not None:
            self.df_train = X_train.join(y_train)
        else:
            self.df_train = X_train
        if isinstance(self.df_train, psDataFrame):
            self.df_train = self.df_train.to_spark(index_col=index_col)
        if return_label:
            return self.df_train, y_train.name
        else:
            return self.df_train

    def fit(
        self,
        X_train: psDataFrame,
        y_train: psSeries = None,
        budget=None,
        free_mem_ratio=0,
        index_col: str = "tmp_index_col",
        **kwargs,
    ):
        """Train the model from given training data.
        Args:
            X_train: A pyspark.pandas DataFrame of training data in shape n*m.
            y_train: A pyspark.pandas Series in shape n*1. None if X_train is a pyspark.pandas
                Dataframe contains y_train.
            budget: A float of the time budget in seconds.
            free_mem_ratio: A float between 0 and 1 for the free memory ratio to keep during training.
        Returns:
            train_time: A float of the training time in seconds.
        """
        df_train, label_col = self._preprocess(X_train, y_train, index_col=index_col, return_label=True)
        kwargs["labelCol"] = label_col
        train_time = self._fit(df_train, **kwargs)
        return train_time

    def _fit(self, df_train: sparkDataFrame, **kwargs):
        current_time = time.time()
        pipeline_model = self.estimator_class(**self.params, **kwargs)
        if logger.level == logging.DEBUG:
            logger.debug(f"flaml.model - {pipeline_model} fit started with params {self.params}")
        pipeline_model.fit(df_train)
        if logger.level == logging.DEBUG:
            logger.debug(f"flaml.model - {pipeline_model} fit finished")
        train_time = time.time() - current_time
        self._model = pipeline_model
        return train_time

    def predict(self, X, index_col="tmp_index_col", return_all=False, **kwargs):
        """Predict label from features.
        Args:
            X: A pyspark or pyspark.pandas dataframe of featurized instances, shape n*m.
            index_col: A str of the index column name. Default to "tmp_index_col".
            return_all: A bool of whether to return all the prediction results. Default to False.
        Returns:
            A pyspark.pandas series of shape n*1 if return_all is False. Otherwise, a pyspark.pandas dataframe.
        """
        if self._model is not None:
            X = self._preprocess(X, index_col=index_col)
            predictions = to_pandas_on_spark(self._model.transform(X), index_col=index_col)
            predictions.index.name = None
            pred_y = predictions["prediction"]
            if return_all:
                return predictions
            else:
                return pred_y
        else:
            logger.warning("Estimator is not fit yet. Please run fit() before predict().")
            return np.ones(X.shape[0])

    def predict_proba(self, X, index_col="tmp_index_col", return_all=False, **kwargs):
        """Predict the probability of each class from features.
        Only works for classification problems
        Args:
            X: A pyspark or pyspark.pandas dataframe of featurized instances, shape n*m.
            index_col: A str of the index column name. Default to "tmp_index_col".
            return_all: A bool of whether to return all the prediction results. Default to False.
        Returns:
            A pyspark.pandas dataframe of shape n*c. c is the # classes.
            Each element at (i,j) is the probability for instance i to be in
                class j.
        """
        assert self._task.is_classification(), "predict_proba() only for classification."
        if self._model is not None:
            X = self._preprocess(X, index_col=index_col)
            predictions = to_pandas_on_spark(self._model.transform(X), index_col=index_col)
            predictions.index.name = None
            pred_y = predictions["probability"]

            if return_all:
                return predictions
            else:
                return pred_y
        else:
            logger.warning("Estimator is not fit yet. Please run fit() before predict().")
            return np.ones(X.shape[0])


class SparkLGBMEstimator(SparkEstimator):
    """The class for fine-tuning spark version lightgbm models, using SynapseML API."""

    ITER_HP = "numIterations"
    DEFAULT_ITER = 100

    @classmethod
    def search_space(cls, data_size, **params):
        upper = max(5, min(32768, int(data_size[0])))  # upper must be larger than lower
        # https://github.com/microsoft/SynapseML/blob/master/lightgbm/src/main/scala/com/microsoft/azure/synapse/ml/lightgbm/LightGBMBase.scala
        return {
            "numIterations": {
                "domain": tune.lograndint(lower=4, upper=upper),
                "init_value": 4,
                "low_cost_init_value": 4,
            },
            "numLeaves": {
                "domain": tune.lograndint(lower=4, upper=upper),
                "init_value": 4,
                "low_cost_init_value": 4,
            },
            "minDataInLeaf": {
                "domain": tune.lograndint(lower=2, upper=2**7 + 1),
                "init_value": 20,
            },
            "learningRate": {
                "domain": tune.loguniform(lower=1 / 1024, upper=1.0),
                "init_value": 0.1,
            },
            "log_max_bin": {  # log transformed with base 2
                "domain": tune.lograndint(lower=3, upper=11),
                "init_value": 8,
            },
            "featureFraction": {
                "domain": tune.uniform(lower=0.01, upper=1.0),
                "init_value": 1.0,
            },
            "lambdaL1": {
                "domain": tune.loguniform(lower=1 / 1024, upper=1024),
                "init_value": 1 / 1024,
            },
            "lambdaL2": {
                "domain": tune.loguniform(lower=1 / 1024, upper=1024),
                "init_value": 1.0,
            },
        }

    def config2params(self, config: dict) -> dict:
        params = super().config2params(config)
        if "n_jobs" in params:
            params.pop("n_jobs")
        if "log_max_bin" in params:
            params["maxBin"] = (1 << params.pop("log_max_bin")) - 1
        return params

    @classmethod
    def size(cls, config):
        num_leaves = int(round(config.get("numLeaves") or 1 << config.get("maxDepth", 16)))
        n_estimators = int(round(config["numIterations"]))
        return (num_leaves * 3 + (num_leaves - 1) * 4 + 1.0) * n_estimators * 8

    def __init__(self, task="binary", **config):
        super().__init__(task, **config)
        err_msg = (
            "SynapseML is not installed. Please refer to [SynapseML]"
            + "(https://github.com/microsoft/SynapseML) for installation instructions."
        )
        if "regression" == task:
            try:
                from synapse.ml.lightgbm import LightGBMRegressor
            except ImportError:
                raise ImportError(err_msg)

            self.estimator_class = LightGBMRegressor
            self.estimator_params = ParamList_LightGBM_Regressor
        elif "rank" == task:
            try:
                from synapse.ml.lightgbm import LightGBMRanker
            except ImportError:
                raise ImportError(err_msg)

            self.estimator_class = LightGBMRanker
            self.estimator_params = ParamList_LightGBM_Ranker
        else:
            try:
                from synapse.ml.lightgbm import LightGBMClassifier
            except ImportError:
                raise ImportError(err_msg)

            self.estimator_class = LightGBMClassifier
            self.estimator_params = ParamList_LightGBM_Classifier
        self._time_per_iter = None
        self._train_size = 0
        self._mem_per_iter = -1
        self.model_classes_ = None
        self.model_n_classes_ = None

    def fit(
        self,
        X_train,
        y_train=None,
        budget=None,
        free_mem_ratio=0,
        index_col="tmp_index_col",
        **kwargs,
    ):
        start_time = time.time()
        if self.model_n_classes_ is None and self._task not in ["regression", "rank"]:
            self.model_n_classes_, self.model_classes_ = len_labels(y_train, return_labels=True)
        df_train, label_col = self._preprocess(X_train, y_train, index_col=index_col, return_label=True)
        # n_iter = self.params.get(self.ITER_HP, self.DEFAULT_ITER)
        # trained = False
        # mem0 = psutil.virtual_memory().available if psutil is not None else 1
        _kwargs = kwargs.copy()
        if self._task not in ["regression", "rank"] and "objective" not in _kwargs:
            _kwargs["objective"] = "binary" if self.model_n_classes_ == 2 else "multiclass"
        for k in list(_kwargs.keys()):
            if k not in self.estimator_params:
                logger.warning(f"[SparkLGBMEstimator] [Warning] Ignored unknown parameter: {k}")
                _kwargs.pop(k)
        # TODO: find a better estimation of early stopping
        # if (
        #     (not self._time_per_iter or abs(self._train_size - df_train.count()) > 4)
        #     and budget is not None
        #     or self._mem_per_iter < 0
        #     and psutil is not None
        # ) and n_iter > 1:
        #     self.params[self.ITER_HP] = 1
        #     self._t1 = self._fit(df_train, **_kwargs)
        #     if budget is not None and self._t1 >= budget or n_iter == 1:
        #         return self._t1
        #     mem1 = psutil.virtual_memory().available if psutil is not None else 1
        #     self._mem1 = mem0 - mem1
        #     self.params[self.ITER_HP] = min(n_iter, 4)
        #     self._t2 = self._fit(df_train, **_kwargs)
        #     mem2 = psutil.virtual_memory().available if psutil is not None else 1
        #     self._mem2 = max(mem0 - mem2, self._mem1)
        #     self._mem_per_iter = min(self._mem1, self._mem2 / self.params[self.ITER_HP])
        #     self._time_per_iter = (
        #         (self._t2 - self._t1) / (self.params[self.ITER_HP] - 1)
        #         if self._t2 > self._t1
        #         else self._t1
        #         if self._t1
        #         else 0.001
        #     )
        #     self._train_size = df_train.count()
        #     if (
        #         budget is not None
        #         and self._t1 + self._t2 >= budget
        #         or n_iter == self.params[self.ITER_HP]
        #     ):
        #         # self.params[self.ITER_HP] = n_iter
        #         return time.time() - start_time
        #     trained = True
        # if n_iter > 1:
        #     max_iter = min(
        #         n_iter,
        #         int(
        #             (budget - time.time() + start_time - self._t1) / self._time_per_iter
        #             + 1
        #         )
        #         if budget is not None
        #         else n_iter,
        #     )
        #     if trained and max_iter <= self.params[self.ITER_HP]:
        #         return time.time() - start_time
        #     # when not trained, train at least one iter
        #     self.params[self.ITER_HP] = max(max_iter, 1)
        _kwargs["labelCol"] = label_col
        self._fit(df_train, **_kwargs)
        train_time = time.time() - start_time
        return train_time

    def _fit(self, df_train: sparkDataFrame, **kwargs):
        current_time = time.time()
        model = self.estimator_class(**self.params, **kwargs)
        if logger.level == logging.DEBUG:
            logger.debug(f"flaml.model - {model} fit started with params {self.params}")
        self._model = model.fit(df_train)
        self._model.classes_ = self.model_classes_
        self._model.n_classes_ = self.model_n_classes_
        if logger.level == logging.DEBUG:
            logger.debug(f"flaml.model - {model} fit finished")
        train_time = time.time() - current_time
        return train_time


class TransformersEstimator(BaseEstimator):
    """The class for fine-tuning language models, using huggingface transformers API."""

    ITER_HP = "global_max_steps"

    def __init__(self, task="seq-classification", **config):
        super().__init__(task, **config)
        import uuid

        self.trial_id = str(uuid.uuid1().hex)[:8]
        if task not in NLG_TASKS:  # TODO: not in NLG_TASKS
            from .nlp.huggingface.training_args import (
                TrainingArgumentsForAuto as TrainingArguments,
            )
        else:
            from .nlp.huggingface.training_args import (
                Seq2SeqTrainingArgumentsForAuto as TrainingArguments,
            )
        self._TrainingArguments = TrainingArguments

    @classmethod
    def search_space(cls, data_size, task, **params):
        search_space_dict = {
            "learning_rate": {
                "domain": tune.loguniform(1e-6, 1e-4),
                "init_value": 1e-5,
            },
            "num_train_epochs": {
                "domain": tune.choice([1, 2, 3, 4, 5]),
                "init_value": 3,  # to be consistent with roberta
                "low_cost_init_value": 1,
            },
            "per_device_train_batch_size": {
                "domain": tune.choice([4, 8, 16, 32, 64]),
                "init_value": 32,
                "low_cost_init_value": 64,
            },
            "seed": {
                "domain": tune.choice(range(1, 40)),
                "init_value": 20,
            },
            "global_max_steps": {
                "domain": sys.maxsize,
                "init_value": sys.maxsize,
            },
        }

        return search_space_dict

    @property
    def fp16(self):
        return self._kwargs.get("gpu_per_trial") and self._training_args.fp16

    @property
    def no_cuda(self):
        return not self._kwargs.get("gpu_per_trial")

    def _set_training_args(self, **kwargs):
        from .nlp.utils import date_str, Counter

        for key, val in kwargs.items():
            assert key not in self.params, (
                "Since {} is in the search space, it cannot exist in 'custom_fit_kwargs' at the same time."
                "If you need to fix the value of {} to {}, the only way is to add a single-value domain in the search "
                "space by adding:\n '{}': {{ 'domain': {} }} to 'custom_hp'. For example:"
                'automl_settings["custom_hp"] = {{ "transformer": {{ "model_path": {{ "domain" : '
                '"google/electra-small-discriminator" }} }} }}'.format(key, key, val, key, val)
            )

        """
            If use has specified any custom args for TrainingArguments, update these arguments
        """
        self._training_args = self._TrainingArguments(**kwargs)

        """
            Update the attributes in TrainingArguments with self.params values
        """
        for key, val in self.params.items():
            if hasattr(self._training_args, key):
                setattr(self._training_args, key, val)

        """
            Update the attributes in TrainingArguments that depends on the values of self.params
        """
        local_dir = os.path.join(self._training_args.output_dir, "train_{}".format(date_str()))
        if self._use_ray is True:
            import ray

            self._training_args.output_dir = ray.tune.get_trial_dir()
        else:
            self._training_args.output_dir = Counter.get_trial_fold_name(local_dir, self.params, self.trial_id)

        self._training_args.fp16 = self.fp16
        self._training_args.no_cuda = self.no_cuda

        if self._task == TOKENCLASSIFICATION and self._training_args.max_seq_length is not None:
            logger.warning(
                "For token classification task, FLAML currently does not support customizing the max_seq_length, max_seq_length will be reset to None."
            )
            setattr(self._training_args, "max_seq_length", None)

    def _tokenize_text(self, X, y=None, **kwargs):
        from .nlp.huggingface.utils import tokenize_text
        from .nlp.utils import is_a_list_of_str

        is_str = str(X.dtypes[0]) in ("string", "str")
        is_list_of_str = is_a_list_of_str(X[list(X.keys())[0]].to_list()[0])

        if is_str or is_list_of_str:
            return tokenize_text(
                X=X,
                Y=y,
                task=self._task,
                hf_args=self._training_args,
                tokenizer=self.tokenizer,
            )
        else:
            return X, y

    def _model_init(self):
        from .nlp.huggingface.utils import load_model

        this_model = load_model(
            checkpoint_path=self._training_args.model_path,
            task=self._task,
            num_labels=self.num_labels,
        )
        return this_model

    def _preprocess_data(self, X, y):
        from datasets import Dataset

        processed_X, processed_y_df = self._tokenize_text(X=X, y=y, **self._kwargs)
        # convert y from pd.DataFrame back to pd.Series
        processed_y = processed_y_df.iloc[:, 0]

        processed_dataset = Dataset.from_pandas(processed_X.join(processed_y_df))

        return processed_dataset, processed_X, processed_y

    @property
    def num_labels(self):
        if self._task == SEQREGRESSION:
            return 1
        elif self._task == SEQCLASSIFICATION:
            return len(set(self._y_train))
        elif self._task == TOKENCLASSIFICATION:
            return len(self._training_args.label_list)
        else:
            return None

    @property
    def tokenizer(self):
        from transformers import AutoTokenizer

        if self._task == SUMMARIZATION:
            return AutoTokenizer.from_pretrained(
                pretrained_model_name_or_path=self._training_args.model_path,
                cache_dir=None,
                use_fast=True,
                revision="main",
                use_auth_token=None,
            )
        else:
            return AutoTokenizer.from_pretrained(
                self._training_args.model_path,
                use_fast=True,
                add_prefix_space=self._add_prefix_space,
            )

    @property
    def data_collator(self):
        from flaml.automl.task.task import Task
        from flaml.automl.nlp.huggingface.data_collator import (
            task_to_datacollator_class,
        )

        data_collator_class = task_to_datacollator_class.get(
            self._task.name if isinstance(self._task, Task) else self._task
        )

        if data_collator_class:
            kwargs = {
                "model": self._model_init(),
                # need to set model, or there's ValueError: Expected input batch_size (..) to match target batch_size (..)
                "label_pad_token_id": -100,  # pad with token id -100
                "pad_to_multiple_of": 8,
                # pad to multiple of 8 because quote Transformers: "This is especially useful to enable the use of Tensor Cores on NVIDIA hardware with compute capability >= 7.5 (Volta)"
                "tokenizer": self.tokenizer,
            }

            for key in list(kwargs.keys()):
                if key not in data_collator_class.__dict__.keys() and key != "tokenizer":
                    del kwargs[key]
            return data_collator_class(**kwargs)
        else:
            return None

    def fit(
        self,
        X_train: DataFrame,
        y_train: Series,
        budget=None,
        free_mem_ratio=0,
        X_val=None,
        y_val=None,
        gpu_per_trial=None,
        metric=None,
        **kwargs,
    ):
        import transformers

        transformers.logging.set_verbosity_error()

        from transformers import TrainerCallback
        from transformers.trainer_utils import set_seed
        from .nlp.huggingface.trainer import TrainerForAuto

        try:
            from ray.tune import is_session_enabled

            self._use_ray = is_session_enabled()
        except ImportError:
            self._use_ray = False

        this_params = self.params
        self._kwargs = kwargs

        self._X_train, self._y_train = X_train, y_train
        self._set_training_args(**kwargs)
        self._add_prefix_space = (
            "roberta" in self._training_args.model_path
        )  # If using roberta model, must set add_prefix_space to True to avoid the assertion error at
        # https://github.com/huggingface/transformers/blob/main/src/transformers/models/roberta/tokenization_roberta_fast.py#L249

        train_dataset, self._X_train, self._y_train = self._preprocess_data(X_train, y_train)
        if X_val is not None:
            eval_dataset, self._X_val, self._y_val = self._preprocess_data(X_val, y_val)
        else:
            eval_dataset, self._X_val, self._y_val = None, None, None

        set_seed(self.params.get("seed", self._training_args.seed))
        self._metric = metric

        class EarlyStoppingCallbackForAuto(TrainerCallback):
            def on_train_begin(self, args, state, control, **callback_kwargs):
                self.train_begin_time = time.time()

            def on_step_begin(self, args, state, control, **callback_kwargs):
                self.step_begin_time = time.time()

            def on_step_end(self, args, state, control, **callback_kwargs):
                if state.global_step == 1:
                    self.time_per_iter = time.time() - self.step_begin_time
                if (
                    budget
                    and (time.time() + self.time_per_iter > self.train_begin_time + budget)
                    or state.global_step >= this_params[TransformersEstimator.ITER_HP]
                ):
                    control.should_training_stop = True
                    control.should_save = True
                    control.should_evaluate = True
                return control

            def on_epoch_end(self, args, state, control, **callback_kwargs):
                if control.should_training_stop or state.epoch + 1 >= args.num_train_epochs:
                    control.should_save = True
                    control.should_evaluate = True

        self._trainer = TrainerForAuto(
            args=self._training_args,
            model_init=self._model_init,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            tokenizer=self.tokenizer,
            data_collator=self.data_collator,
            compute_metrics=self._compute_metrics_by_dataset_name,
            callbacks=[EarlyStoppingCallbackForAuto],
        )

        if self._task in NLG_TASKS:
            setattr(self._trainer, "_is_seq2seq", True)

        """
            When not using ray for tuning, set the limit of CUDA_VISIBLE_DEVICES to math.ceil(gpu_per_trial),
            so each estimator does not see all the GPUs
        """
        if gpu_per_trial is not None:
            tmp_cuda_visible_devices = os.environ.get("CUDA_VISIBLE_DEVICES", "")
            self._trainer.args._n_gpu = gpu_per_trial

            # if gpu_per_trial == 0:
            #     os.environ["CUDA_VISIBLE_DEVICES"] = ""
            if tmp_cuda_visible_devices.count(",") != math.ceil(gpu_per_trial) - 1:
                os.environ["CUDA_VISIBLE_DEVICES"] = ",".join([str(x) for x in range(math.ceil(gpu_per_trial))])

        import time

        start_time = time.time()
        self._trainer.train()

        if gpu_per_trial is not None:
            os.environ["CUDA_VISIBLE_DEVICES"] = tmp_cuda_visible_devices

        self.params[self.ITER_HP] = self._trainer.state.global_step

        self._checkpoint_path = self._select_checkpoint(self._trainer)
        self._ckpt_remains = list(self._trainer.ckpt_to_metric.keys())

        if hasattr(self._trainer, "intermediate_results"):
            self.intermediate_results = [
                x[1] for x in sorted(self._trainer.intermediate_results.items(), key=lambda x: x[0])
            ]
        self._trainer = None

        return time.time() - start_time

    def _delete_one_ckpt(self, ckpt_location):
        if self._use_ray is False:
            if os.path.exists(ckpt_location):
                shutil.rmtree(ckpt_location)

    def cleanup(self):
        super().cleanup()
        if hasattr(self, "_ckpt_remains"):
            for each_ckpt in self._ckpt_remains:
                self._delete_one_ckpt(each_ckpt)

    def _select_checkpoint(self, trainer):
        from transformers.trainer_utils import PREFIX_CHECKPOINT_DIR

        if trainer.ckpt_to_metric:
            best_ckpt, _ = min(trainer.ckpt_to_metric.items(), key=lambda x: x[1]["eval_automl_metric"])
            best_ckpt_global_step = trainer.ckpt_to_global_step[best_ckpt]
            for each_ckpt in list(trainer.ckpt_to_metric):
                if each_ckpt != best_ckpt:
                    del trainer.ckpt_to_metric[each_ckpt]
                    del trainer.ckpt_to_global_step[each_ckpt]
                    self._delete_one_ckpt(each_ckpt)
        else:
            best_ckpt_global_step = trainer.state.global_step
            best_ckpt = os.path.join(
                trainer.args.output_dir,
                f"{PREFIX_CHECKPOINT_DIR}-{best_ckpt_global_step}",
            )
        self.params[self.ITER_HP] = best_ckpt_global_step
        logger.debug(trainer.state.global_step)
        logger.debug(trainer.ckpt_to_global_step)
        return best_ckpt

    def _compute_metrics_by_dataset_name(self, eval_pred):
        # TODO: call self._metric(eval_pred, self)
        if isinstance(self._metric, str):
            from .ml import metric_loss_score
            from .nlp.huggingface.utils import postprocess_prediction_and_true

            predictions, y_true = eval_pred
            # postprocess the matrix prediction and ground truth into user readable format, e.g., for summarization, decode into text
            processed_predictions, processed_y_true = postprocess_prediction_and_true(
                task=self._task,
                y_pred=predictions,
                tokenizer=self.tokenizer,
                hf_args=self._training_args,
                y_true=y_true,
            )
            metric_dict = {
                "automl_metric": metric_loss_score(
                    metric_name=self._metric,
                    y_processed_predict=processed_predictions,
                    y_processed_true=processed_y_true,
                    labels=self._training_args.label_list,
                )
            }
        else:
            # TODO: debug to see how custom metric can take both tokenized (here) and untokenized input (ml.py)
            loss, metric_dict = self._metric(
                X_test=self._X_val,
                y_test=self._y_val,
                estimator=self,
                labels=None,
                X_train=self._X_train,
                y_train=self._y_train,
            )
            metric_dict["automl_metric"] = loss

        return metric_dict

    def _init_model_for_predict(self):
        from .nlp.huggingface.trainer import TrainerForAuto

        """
            Need to reinit training_args because of a bug in deepspeed: if not reinit, the deepspeed config will be inconsistent
            with HF config https://github.com/huggingface/transformers/blob/main/src/transformers/training_args.py#L947
        """
        training_args = self._TrainingArguments(local_rank=-1, model_path=self._checkpoint_path, fp16=self.fp16)
        for key, val in self._training_args.__dict__.items():
            if key not in ("local_rank", "model_path", "fp16"):
                setattr(training_args, key, val)
        self._training_args = training_args

        new_trainer = TrainerForAuto(
            model=self._model_init(),
            args=self._training_args,
            data_collator=self.data_collator,
            compute_metrics=self._compute_metrics_by_dataset_name,
        )
        if self._task in NLG_TASKS:
            setattr(new_trainer, "_is_seq2seq", True)
        return new_trainer

    def predict_proba(self, X, **pred_kwargs):
        from datasets import Dataset

        if pred_kwargs:
            for key, val in pred_kwargs.items():
                setattr(self._training_args, key, val)

        assert self._task.is_classification(), "predict_proba() only for classification tasks."

        X_test, _ = self._tokenize_text(X, **self._kwargs)
        test_dataset = Dataset.from_pandas(X_test)

        new_trainer = self._init_model_for_predict()
        try:
            predictions = new_trainer.predict(test_dataset).predictions
        except ZeroDivisionError:
            logger.warning("Zero division error appeared in HuggingFace Transformers.")
            predictions = None
        return predictions

    def score(self, X_val: DataFrame, y_val: Series, **kwargs):
        import transformers

        transformers.logging.set_verbosity_error()

        self._metric = kwargs["metric"]

        eval_dataset, X_val, y_val = self._preprocess_data(X_val, y_val)

        new_trainer = self._init_model_for_predict()
        return new_trainer.evaluate(eval_dataset)

    def predict(self, X, **pred_kwargs):
        import transformers
        from datasets import Dataset
        from .nlp.huggingface.utils import postprocess_prediction_and_true

        transformers.logging.set_verbosity_error()

        if pred_kwargs:
            for key, val in pred_kwargs.items():
                setattr(self._training_args, key, val)

        X_test, _ = self._tokenize_text(X, **self._kwargs)
        test_dataset = Dataset.from_pandas(X_test)

        new_trainer = self._init_model_for_predict()

        kwargs = {} if self._task not in NLG_TASKS else {"metric_key_prefix": "predict"}
        try:
            predictions = new_trainer.predict(test_dataset, **kwargs).predictions
        except ZeroDivisionError:
            logger.warning("Zero division error appeared in HuggingFace Transformers.")
            predictions = None
        post_y_pred, _ = postprocess_prediction_and_true(
            task=self._task,
            y_pred=predictions,
            tokenizer=self.tokenizer,
            hf_args=self._training_args,
            X=X,
        )
        return post_y_pred

    def config2params(self, config: dict) -> dict:
        params = super().config2params(config)
        params[TransformersEstimator.ITER_HP] = params.get(TransformersEstimator.ITER_HP, sys.maxsize)
        return params


class TransformersEstimatorModelSelection(TransformersEstimator):
    def __init__(self, task="seq-classification", **config):
        super().__init__(task, **config)

    @classmethod
    def search_space(cls, data_size, task, **params):
        search_space_dict = TransformersEstimator.search_space(data_size, task, **params)

        """
            For model selection, use the same search space regardless of memory constraint
            If OOM, user should change the search space themselves
        """

        search_space_dict["model_path"] = {
            "domain": tune.choice(
                [
                    "google/electra-base-discriminator",
                    "bert-base-uncased",
                    "roberta-base",
                    "facebook/muppet-roberta-base",
                    "google/electra-small-discriminator",
                ]
            ),
            "init_value": "facebook/muppet-roberta-base",
        }
        return search_space_dict


class SKLearnEstimator(BaseEstimator):
    """
    The base class for tuning scikit-learn estimators.

    Subclasses can modify the function signature of ``__init__`` to
    ignore the values in ``config`` that are not relevant to the constructor
    of their underlying estimator. For example, some regressors in ``scikit-learn``
    don't accept the ``n_jobs`` parameter contained in ``config``. For these,
    one can add ``n_jobs=None,`` before ``**config`` to make sure ``config`` doesn't
    contain an ``n_jobs`` key.
    """

    def __init__(self, task="binary", **config):
        super().__init__(task, **config)

    def _preprocess(self, X):
        if isinstance(X, DataFrame):
            cat_columns = X.select_dtypes(include=["category"]).columns
            if not cat_columns.empty:
                X = X.copy()
                X[cat_columns] = X[cat_columns].apply(lambda x: x.cat.codes)
        elif isinstance(X, np.ndarray) and X.dtype.kind not in "buif":
            # numpy array is not of numeric dtype
            X = DataFrame(X)
            for col in X.columns:
                if isinstance(X[col][0], str):
                    X[col] = X[col].astype("category").cat.codes
            X = X.to_numpy()
        return X


class LGBMEstimator(BaseEstimator):
    """The class for tuning LGBM, using sklearn API."""

    ITER_HP = "n_estimators"
    HAS_CALLBACK = True
    DEFAULT_ITER = 100

    @classmethod
    def search_space(cls, data_size, **params):
        upper = max(5, min(32768, int(data_size[0])))  # upper must be larger than lower
        return {
            "n_estimators": {
                "domain": tune.lograndint(lower=4, upper=upper),
                "init_value": 4,
                "low_cost_init_value": 4,
            },
            "num_leaves": {
                "domain": tune.lograndint(lower=4, upper=upper),
                "init_value": 4,
                "low_cost_init_value": 4,
            },
            "min_child_samples": {
                "domain": tune.lograndint(lower=2, upper=2**7 + 1),
                "init_value": 20,
            },
            "learning_rate": {
                "domain": tune.loguniform(lower=1 / 1024, upper=1.0),
                "init_value": 0.1,
            },
            "log_max_bin": {  # log transformed with base 2
                "domain": tune.lograndint(lower=3, upper=11),
                "init_value": 8,
            },
            "colsample_bytree": {
                "domain": tune.uniform(lower=0.01, upper=1.0),
                "init_value": 1.0,
            },
            "reg_alpha": {
                "domain": tune.loguniform(lower=1 / 1024, upper=1024),
                "init_value": 1 / 1024,
            },
            "reg_lambda": {
                "domain": tune.loguniform(lower=1 / 1024, upper=1024),
                "init_value": 1.0,
            },
        }

    def config2params(self, config: dict) -> dict:
        params = super().config2params(config)
        if "log_max_bin" in params:
            params["max_bin"] = (1 << params.pop("log_max_bin")) - 1
        return params

    @classmethod
    def size(cls, config):
        num_leaves = int(
            round(config.get("num_leaves") or config.get("max_leaves") or 1 << config.get("max_depth", 16))
        )
        n_estimators = int(round(config["n_estimators"]))
        return (num_leaves * 3 + (num_leaves - 1) * 4 + 1.0) * n_estimators * 8

    def __init__(self, task="binary", **config):
        super().__init__(task, **config)
        if "verbose" not in self.params:
            self.params["verbose"] = -1

        if self._task.is_classification():
            self.estimator_class = LGBMClassifier
        elif task == "rank":
            self.estimator_class = LGBMRanker
        else:
            self.estimator_class = LGBMRegressor

        self._time_per_iter = None
        self._train_size = 0
        self._mem_per_iter = -1
        self.HAS_CALLBACK = self.HAS_CALLBACK and self._callbacks(0, 0, 0) is not None

    def _preprocess(self, X):
        if not isinstance(X, DataFrame) and issparse(X) and np.issubdtype(X.dtype, np.integer):
            X = X.astype(float)
        elif isinstance(X, np.ndarray) and X.dtype.kind not in "buif":
            # numpy array is not of numeric dtype
            X = DataFrame(X)
            for col in X.columns:
                if isinstance(X[col][0], str):
                    X[col] = X[col].astype("category").cat.codes
            X = X.to_numpy()
        return X

    def fit(self, X_train, y_train, budget=None, free_mem_ratio=0, **kwargs):
        start_time = time.time()
        deadline = start_time + budget if budget else np.inf
        n_iter = self.params.get(self.ITER_HP, self.DEFAULT_ITER)
        trained = False
        if not self.HAS_CALLBACK:
            mem0 = psutil.virtual_memory().available if psutil is not None else 1
            if (
                (not self._time_per_iter or abs(self._train_size - X_train.shape[0]) > 4)
                and budget is not None
                or self._mem_per_iter < 0
                and psutil is not None
            ) and n_iter > 1:
                self.params[self.ITER_HP] = 1
                self._t1 = self._fit(X_train, y_train, **kwargs)
                if budget is not None and self._t1 >= budget or n_iter == 1:
                    return self._t1
                mem1 = psutil.virtual_memory().available if psutil is not None else 1
                self._mem1 = mem0 - mem1
                self.params[self.ITER_HP] = min(n_iter, 4)
                self._t2 = self._fit(X_train, y_train, **kwargs)
                mem2 = psutil.virtual_memory().available if psutil is not None else 1
                self._mem2 = max(mem0 - mem2, self._mem1)
                # if self._mem1 <= 0:
                #     self._mem_per_iter = self._mem2 / (self.params[self.ITER_HP] + 1)
                # elif self._mem2 <= 0:
                #     self._mem_per_iter = self._mem1
                # else:
                self._mem_per_iter = min(self._mem1, self._mem2 / self.params[self.ITER_HP])
                # if self._mem_per_iter <= 1 and psutil is not None:
                #     n_iter = self.params[self.ITER_HP]
                self._time_per_iter = (
                    (self._t2 - self._t1) / (self.params[self.ITER_HP] - 1)
                    if self._t2 > self._t1
                    else self._t1
                    if self._t1
                    else 0.001
                )
                self._train_size = X_train.shape[0]
                if budget is not None and self._t1 + self._t2 >= budget or n_iter == self.params[self.ITER_HP]:
                    # self.params[self.ITER_HP] = n_iter
                    return time.time() - start_time
                trained = True
            # logger.debug(mem0)
            # logger.debug(self._mem_per_iter)
            if n_iter > 1:
                max_iter = min(
                    n_iter,
                    int((budget - time.time() + start_time - self._t1) / self._time_per_iter + 1)
                    if budget is not None
                    else n_iter,
                    int((1 - free_mem_ratio) * mem0 / self._mem_per_iter)
                    if psutil is not None and self._mem_per_iter > 0
                    else n_iter,
                )
                if trained and max_iter <= self.params[self.ITER_HP]:
                    return time.time() - start_time
                # when not trained, train at least one iter
                self.params[self.ITER_HP] = max(max_iter, 1)
        if self.HAS_CALLBACK:
            kwargs_callbacks = kwargs.get("callbacks")
            if kwargs_callbacks:
                callbacks = kwargs_callbacks + self._callbacks(start_time, deadline, free_mem_ratio)
                kwargs.pop("callbacks")
            else:
                callbacks = self._callbacks(start_time, deadline, free_mem_ratio)
            if isinstance(self, XGBoostSklearnEstimator):
                from xgboost import __version__

                if __version__ >= "1.6.0":
                    # since xgboost>=1.6.0, callbacks can't be passed in fit()
                    self.params["callbacks"] = callbacks
                    callbacks = None
            self._fit(
                X_train,
                y_train,
                callbacks=callbacks,
                **kwargs,
            )
            if callbacks is None:
                # for xgboost>=1.6.0, pop callbacks to enable pickle
                callbacks = self.params.pop("callbacks")
                self._model.set_params(callbacks=callbacks[:-1])
            best_iteration = (
                self._model.get_booster().best_iteration
                if isinstance(self, XGBoostSklearnEstimator)
                else self._model.best_iteration_
            )
            if best_iteration is not None:
                self._model.set_params(n_estimators=best_iteration + 1)
        else:
            self._fit(X_train, y_train, **kwargs)
        train_time = time.time() - start_time
        return train_time

    def _callbacks(self, start_time, deadline, free_mem_ratio) -> List[Callable]:
        return [partial(self._callback, start_time, deadline, free_mem_ratio)]

    def _callback(self, start_time, deadline, free_mem_ratio, env) -> None:
        from lightgbm.callback import EarlyStopException

        now = time.time()
        if env.iteration == 0:
            self._time_per_iter = now - start_time
        if now + self._time_per_iter > deadline:
            raise EarlyStopException(env.iteration, env.evaluation_result_list)
        if psutil is not None:
            mem = psutil.virtual_memory()
            if mem.available / mem.total < free_mem_ratio:
                raise EarlyStopException(env.iteration, env.evaluation_result_list)


class XGBoostEstimator(SKLearnEstimator):
    """The class for tuning XGBoost regressor, not using sklearn API."""

    DEFAULT_ITER = 10

    @classmethod
    def search_space(cls, data_size, **params):
        upper = max(5, min(32768, int(data_size[0])))  # upper must be larger than lower
        return {
            "n_estimators": {
                "domain": tune.lograndint(lower=4, upper=upper),
                "init_value": 4,
                "low_cost_init_value": 4,
            },
            "max_leaves": {
                "domain": tune.lograndint(lower=4, upper=upper),
                "init_value": 4,
                "low_cost_init_value": 4,
            },
            "max_depth": {
                "domain": tune.choice([0, 6, 12]),
                "init_value": 0,
            },
            "min_child_weight": {
                "domain": tune.loguniform(lower=0.001, upper=128),
                "init_value": 1.0,
            },
            "learning_rate": {
                "domain": tune.loguniform(lower=1 / 1024, upper=1.0),
                "init_value": 0.1,
            },
            "subsample": {
                "domain": tune.uniform(lower=0.1, upper=1.0),
                "init_value": 1.0,
            },
            "colsample_bylevel": {
                "domain": tune.uniform(lower=0.01, upper=1.0),
                "init_value": 1.0,
            },
            "colsample_bytree": {
                "domain": tune.uniform(lower=0.01, upper=1.0),
                "init_value": 1.0,
            },
            "reg_alpha": {
                "domain": tune.loguniform(lower=1 / 1024, upper=1024),
                "init_value": 1 / 1024,
            },
            "reg_lambda": {
                "domain": tune.loguniform(lower=1 / 1024, upper=1024),
                "init_value": 1.0,
            },
        }

    @classmethod
    def size(cls, config):
        return LGBMEstimator.size(config)

    @classmethod
    def cost_relative2lgbm(cls):
        return 1.6

    def config2params(self, config: dict) -> dict:
        params = super().config2params(config)
        max_depth = params["max_depth"] = params.get("max_depth", 0)
        if max_depth == 0:
            params["grow_policy"] = params.get("grow_policy", "lossguide")
            params["tree_method"] = params.get("tree_method", "hist")
        # params["booster"] = params.get("booster", "gbtree")
        params["use_label_encoder"] = params.get("use_label_encoder", False)
        if "n_jobs" in config:
            params["nthread"] = params.pop("n_jobs")
        return params

    def __init__(
        self,
        task="regression",
        **config,
    ):
        super().__init__(task, **config)
        self.params["verbosity"] = 0

    def fit(self, X_train, y_train, budget=None, free_mem_ratio=0, **kwargs):
        import xgboost as xgb

        start_time = time.time()
        deadline = start_time + budget if budget else np.inf
        if issparse(X_train):
            if xgb.__version__ < "1.6.0":
                # "auto" fails for sparse input since xgboost 1.6.0
                self.params["tree_method"] = "auto"
        else:
            X_train = self._preprocess(X_train)
        if "sample_weight" in kwargs:
            dtrain = xgb.DMatrix(X_train, label=y_train, weight=kwargs["sample_weight"])
        else:
            dtrain = xgb.DMatrix(X_train, label=y_train)

        objective = self.params.get("objective")
        if isinstance(objective, str):
            obj = None
        else:
            obj = objective
            if "objective" in self.params:
                del self.params["objective"]
        _n_estimators = self.params.pop("n_estimators")
        callbacks = XGBoostEstimator._callbacks(start_time, deadline, free_mem_ratio)
        if callbacks:
            self._model = xgb.train(
                self.params,
                dtrain,
                _n_estimators,
                obj=obj,
                callbacks=callbacks,
            )
            self.params["n_estimators"] = self._model.best_iteration + 1
        else:
            self._model = xgb.train(self.params, dtrain, _n_estimators, obj=obj)
            self.params["n_estimators"] = _n_estimators
        self.params["objective"] = objective
        del dtrain
        train_time = time.time() - start_time
        return train_time

    def predict(self, X, **kwargs):
        import xgboost as xgb

        if not issparse(X):
            X = self._preprocess(X)
        dtest = xgb.DMatrix(X)
        return super().predict(dtest, **kwargs)

    @classmethod
    def _callbacks(cls, start_time, deadline, free_mem_ratio):
        try:
            from xgboost.callback import TrainingCallback
        except ImportError:  # for xgboost<1.3
            return None

        class ResourceLimit(TrainingCallback):
            def after_iteration(self, model, epoch, evals_log) -> bool:
                now = time.time()
                if epoch == 0:
                    self._time_per_iter = now - start_time
                if now + self._time_per_iter > deadline:
                    return True
                if psutil is not None:
                    mem = psutil.virtual_memory()
                    if mem.available / mem.total < free_mem_ratio:
                        return True
                return False

        return [ResourceLimit()]


class XGBoostSklearnEstimator(SKLearnEstimator, LGBMEstimator):
    """The class for tuning XGBoost with unlimited depth, using sklearn API."""

    DEFAULT_ITER = 10

    @classmethod
    def search_space(cls, data_size, **params):
        space = XGBoostEstimator.search_space(data_size)
        space.pop("max_depth")
        return space

    @classmethod
    def cost_relative2lgbm(cls):
        return XGBoostEstimator.cost_relative2lgbm()

    def config2params(self, config: dict) -> dict:
        params = super().config2params(config)
        max_depth = params["max_depth"] = params.get("max_depth", 0)
        if max_depth == 0:
            params["grow_policy"] = params.get("grow_policy", "lossguide")
            params["tree_method"] = params.get("tree_method", "hist")
        params["use_label_encoder"] = params.get("use_label_encoder", False)
        return params

    def __init__(
        self,
        task="binary",
        **config,
    ):
        super().__init__(task, **config)
        del self.params["verbose"]
        self.params["verbosity"] = 0
        import xgboost as xgb

        if "rank" == task:
            self.estimator_class = xgb.XGBRanker
        elif self._task.is_classification():
            self.estimator_class = xgb.XGBClassifier
        else:
            self.estimator_class = xgb.XGBRegressor

        self._xgb_version = xgb.__version__

    def fit(self, X_train, y_train, budget=None, free_mem_ratio=0, **kwargs):
        if issparse(X_train) and self._xgb_version < "1.6.0":
            # "auto" fails for sparse input since xgboost 1.6.0
            self.params["tree_method"] = "auto"
        if kwargs.get("gpu_per_trial"):
            self.params["tree_method"] = "gpu_hist"
            kwargs.pop("gpu_per_trial")
        return super().fit(X_train, y_train, budget, free_mem_ratio, **kwargs)

    def _callbacks(self, start_time, deadline, free_mem_ratio) -> List[Callable]:
        return XGBoostEstimator._callbacks(start_time, deadline, free_mem_ratio)


class XGBoostLimitDepthEstimator(XGBoostSklearnEstimator):
    """The class for tuning XGBoost with limited depth, using sklearn API."""

    @classmethod
    def search_space(cls, data_size, **params):
        space = XGBoostEstimator.search_space(data_size)
        space.pop("max_leaves")
        upper = max(6, int(np.log2(data_size[0])))
        space["max_depth"] = {
            "domain": tune.randint(lower=1, upper=min(upper, 16)),
            "init_value": 6,
            "low_cost_init_value": 1,
        }
        space["learning_rate"]["init_value"] = 0.3
        space["n_estimators"]["init_value"] = 10
        return space

    @classmethod
    def cost_relative2lgbm(cls):
        return 64


class RandomForestEstimator(SKLearnEstimator, LGBMEstimator):
    """The class for tuning Random Forest."""

    HAS_CALLBACK = False
    nrows = 101

    @classmethod
    def search_space(cls, data_size, task, **params):
        RandomForestEstimator.nrows = int(data_size[0])
        upper = min(2048, RandomForestEstimator.nrows)
        init = 1 / np.sqrt(data_size[1]) if task.is_classification() else 1
        lower = min(0.1, init)
        space = {
            "n_estimators": {
                "domain": tune.lograndint(lower=4, upper=max(5, upper)),
                "init_value": 4,
                "low_cost_init_value": 4,
            },
            "max_features": {
                "domain": tune.loguniform(lower=lower, upper=1.0),
                "init_value": init,
            },
            "max_leaves": {
                "domain": tune.lograndint(
                    lower=4,
                    upper=max(5, min(32768, RandomForestEstimator.nrows >> 1)),  #
                ),
                "init_value": 4,
                "low_cost_init_value": 4,
            },
        }
        if task.is_classification():
            space["criterion"] = {
                "domain": tune.choice(["gini", "entropy"]),
                # "init_value": "gini",
            }
        return space

    @classmethod
    def cost_relative2lgbm(cls):
        return 2

    def config2params(self, config: dict) -> dict:
        params = super().config2params(config)
        if "max_leaves" in params:
            params["max_leaf_nodes"] = params.get("max_leaf_nodes", params.pop("max_leaves"))
        if not self._task.is_classification() and "criterion" in config:
            params.pop("criterion")
        if "random_state" not in params:
            params["random_state"] = 12032022
        return params

    def __init__(
        self,
        task: Task,
        **params,
    ):
        super().__init__(task, **params)
        self.params["verbose"] = 0

        if self._task.is_classification():
            self.estimator_class = RandomForestClassifier
        else:
            self.estimator_class = RandomForestRegressor


class ExtraTreesEstimator(RandomForestEstimator):
    """The class for tuning Extra Trees."""

    @classmethod
    def cost_relative2lgbm(cls):
        return 1.9

    def __init__(self, task="binary", **params):
        if isinstance(task, str):
            from flaml.automl.task.factory import task_factory

            task = task_factory(task)
        super().__init__(task, **params)
        if task.is_regression():
            self.estimator_class = ExtraTreesRegressor
        else:
            self.estimator_class = ExtraTreesClassifier


class LRL1Classifier(SKLearnEstimator):
    """The class for tuning Logistic Regression with L1 regularization."""

    @classmethod
    def search_space(cls, **params):
        return {
            "C": {
                "domain": tune.loguniform(lower=0.03125, upper=32768.0),
                "init_value": 1.0,
            },
        }

    @classmethod
    def cost_relative2lgbm(cls):
        return 160

    def config2params(self, config: dict) -> dict:
        params = super().config2params(config)
        params["tol"] = params.get("tol", 0.0001)
        params["solver"] = params.get("solver", "saga")
        params["penalty"] = params.get("penalty", "l1")
        return params

    def __init__(self, task="binary", **config):
        super().__init__(task, **config)
        assert self._task.is_classification(), "LogisticRegression for classification task only"
        self.estimator_class = LogisticRegression


class LRL2Classifier(SKLearnEstimator):
    """The class for tuning Logistic Regression with L2 regularization."""

    limit_resource = True

    @classmethod
    def search_space(cls, **params):
        return LRL1Classifier.search_space(**params)

    @classmethod
    def cost_relative2lgbm(cls):
        return 25

    def config2params(self, config: dict) -> dict:
        params = super().config2params(config)
        params["tol"] = params.get("tol", 0.0001)
        params["solver"] = params.get("solver", "lbfgs")
        params["penalty"] = params.get("penalty", "l2")
        return params

    def __init__(self, task="binary", **config):
        super().__init__(task, **config)
        assert self._task.is_classification(), "LogisticRegression for classification task only"
        self.estimator_class = LogisticRegression


class CatBoostEstimator(BaseEstimator):
    """The class for tuning CatBoost."""

    ITER_HP = "n_estimators"
    DEFAULT_ITER = 1000

    @classmethod
    def search_space(cls, data_size, **params):
        upper = max(min(round(1500000 / data_size[0]), 150), 12)
        return {
            "early_stopping_rounds": {
                "domain": tune.lograndint(lower=10, upper=upper),
                "init_value": 10,
                "low_cost_init_value": 10,
            },
            "learning_rate": {
                "domain": tune.loguniform(lower=0.005, upper=0.2),
                "init_value": 0.1,
            },
            "n_estimators": {
                "domain": 8192,
                "init_value": 8192,
            },
        }

    @classmethod
    def size(cls, config):
        n_estimators = config.get("n_estimators", 8192)
        max_leaves = 64
        return (max_leaves * 3 + (max_leaves - 1) * 4 + 1.0) * n_estimators * 8

    @classmethod
    def cost_relative2lgbm(cls):
        return 15

    def _preprocess(self, X):
        if isinstance(X, DataFrame):
            cat_columns = X.select_dtypes(include=["category"]).columns
            if not cat_columns.empty:
                X = X.copy()
                X[cat_columns] = X[cat_columns].apply(
                    lambda x: x.cat.rename_categories([str(c) if isinstance(c, float) else c for c in x.cat.categories])
                )
        elif isinstance(X, np.ndarray) and X.dtype.kind not in "buif":
            # numpy array is not of numeric dtype
            X = DataFrame(X)
            for col in X.columns:
                if isinstance(X[col][0], str):
                    X[col] = X[col].astype("category").cat.codes
            X = X.to_numpy()
        return X

    def config2params(self, config: dict) -> dict:
        params = super().config2params(config)
        params["n_estimators"] = params.get("n_estimators", 8192)
        if "n_jobs" in params:
            params["thread_count"] = params.pop("n_jobs")
        return params

    def __init__(
        self,
        task="binary",
        **config,
    ):
        super().__init__(task, **config)
        self.params.update(
            {
                "verbose": config.get("verbose", False),
                "random_seed": config.get("random_seed", 10242048),
            }
        )
        if self._task.is_classification():
            from catboost import CatBoostClassifier

            self.estimator_class = CatBoostClassifier
        else:
            from catboost import CatBoostRegressor

            self.estimator_class = CatBoostRegressor

    def fit(self, X_train, y_train, budget=None, free_mem_ratio=0, **kwargs):
        start_time = time.time()
        deadline = start_time + budget if budget else np.inf
        train_dir = f"catboost_{str(start_time)}"
        X_train = self._preprocess(X_train)
        if isinstance(X_train, DataFrame):
            cat_features = list(X_train.select_dtypes(include="category").columns)
        else:
            cat_features = []
        use_best_model = kwargs.get("use_best_model", True)
        n = max(int(len(y_train) * 0.9), len(y_train) - 1000) if use_best_model else len(y_train)
        X_tr, y_tr = X_train[:n], y_train[:n]
        from catboost import Pool, __version__

        eval_set = Pool(data=X_train[n:], label=y_train[n:], cat_features=cat_features) if use_best_model else None
        if "sample_weight" in kwargs:
            weight = kwargs["sample_weight"]
            if weight is not None:
                kwargs["sample_weight"] = weight[:n]
        else:
            weight = None

        model = self.estimator_class(train_dir=train_dir, **self.params)
        if __version__ >= "0.26":
            model.fit(
                X_tr,
                y_tr,
                cat_features=cat_features,
                eval_set=eval_set,
                callbacks=CatBoostEstimator._callbacks(
                    start_time, deadline, free_mem_ratio if use_best_model else None
                ),
                **kwargs,
            )
        else:
            model.fit(
                X_tr,
                y_tr,
                cat_features=cat_features,
                eval_set=eval_set,
                **kwargs,
            )
        shutil.rmtree(train_dir, ignore_errors=True)
        if weight is not None:
            kwargs["sample_weight"] = weight
        self._model = model
        self.params[self.ITER_HP] = self._model.tree_count_
        train_time = time.time() - start_time
        return train_time

    @classmethod
    def _callbacks(cls, start_time, deadline, free_mem_ratio):
        class ResourceLimit:
            def after_iteration(self, info) -> bool:
                now = time.time()
                if info.iteration == 1:
                    self._time_per_iter = now - start_time
                if now + self._time_per_iter > deadline:
                    return False
                if psutil is not None and free_mem_ratio is not None:
                    mem = psutil.virtual_memory()
                    if mem.available / mem.total < free_mem_ratio:
                        return False
                return True  # can continue

        return [ResourceLimit()]


class KNeighborsEstimator(BaseEstimator):
    @classmethod
    def search_space(cls, data_size, **params):
        upper = min(512, int(data_size[0] / 2))
        return {
            "n_neighbors": {
                "domain": tune.lograndint(lower=1, upper=max(2, upper)),
                "init_value": 5,
                "low_cost_init_value": 1,
            },
        }

    @classmethod
    def cost_relative2lgbm(cls):
        return 30

    def config2params(self, config: dict) -> dict:
        params = super().config2params(config)
        params["weights"] = params.get("weights", "distance")
        return params

    def __init__(self, task="binary", **config):
        super().__init__(task, **config)
        if self._task.is_classification():
            from sklearn.neighbors import KNeighborsClassifier

            self.estimator_class = KNeighborsClassifier
        else:
            from sklearn.neighbors import KNeighborsRegressor

            self.estimator_class = KNeighborsRegressor

    def _preprocess(self, X):
        if isinstance(X, DataFrame):
            cat_columns = X.select_dtypes(["category"]).columns
            if X.shape[1] == len(cat_columns):
                raise ValueError("kneighbor requires at least one numeric feature")
            X = X.drop(cat_columns, axis=1)
        elif isinstance(X, np.ndarray) and X.dtype.kind not in "buif":
            # drop categocial columns if any
            X = DataFrame(X)
            cat_columns = []
            for col in X.columns:
                if isinstance(X[col][0], str):
                    cat_columns.append(col)
            X = X.drop(cat_columns, axis=1)
            X = X.to_numpy()
        return X


class suppress_stdout_stderr(object):
    def __init__(self):
        # Open a pair of null files
        self.null_fds = [os.open(os.devnull, os.O_RDWR) for x in range(2)]
        # Save the actual stdout (1) and stderr (2) file descriptors.
        self.save_fds = (os.dup(1), os.dup(2))

    def __enter__(self):
        # Assign the null pointers to stdout and stderr.
        os.dup2(self.null_fds[0], 1)
        os.dup2(self.null_fds[1], 2)

    def __exit__(self, *_):
        # Re-assign the real stdout/stderr back to (1) and (2)
        os.dup2(self.save_fds[0], 1)
        os.dup2(self.save_fds[1], 2)
        # Close the null files
        os.close(self.null_fds[0])
        os.close(self.null_fds[1])
