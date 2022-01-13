# !
#  * Copyright (c) Microsoft Corporation. All rights reserved.
#  * Licensed under the MIT License. See LICENSE file in the
#  * project root for license information.
import time
import numpy as np
import pandas as pd
from sklearn.metrics import (
    mean_squared_error,
    r2_score,
    roc_auc_score,
    accuracy_score,
    mean_absolute_error,
    log_loss,
    average_precision_score,
    f1_score,
    mean_absolute_percentage_error,
    ndcg_score,
)
from sklearn.model_selection import RepeatedStratifiedKFold, GroupKFold, TimeSeriesSplit
from .model import (
    XGBoostSklearnEstimator,
    XGBoost_TS_Regressor,
    XGBoostLimitDepthEstimator,
    XGBoostLimitDepth_TS_Regressor,
    RandomForestEstimator,
    RF_TS_Regressor,
    LGBMEstimator,
    LGBM_TS_Regressor,
    LRL1Classifier,
    LRL2Classifier,
    CatBoostEstimator,
    ExtraTreesEstimator,
    ExtraTrees_TS_Regressor,
    KNeighborsEstimator,
    Prophet,
    ARIMA,
    SARIMAX,
    TransformersEstimator,
)
from .data import CLASSIFICATION, group_counts, TS_FORECAST, TS_VALUE_COL
import logging

logger = logging.getLogger(__name__)

sklearn_metric_name_set = {
    "r2",
    "rmse",
    "mae",
    "mse",
    "accuracy",
    "roc_auc",
    "roc_auc_ovr",
    "roc_auc_ovo",
    "log_loss",
    "mape",
    "f1",
    "ap",
    "ndcg",
    "micro_f1",
    "macro_f1",
}
huggingface_metric_to_mode = {
    "accuracy": "max",
    "bertscore": "max",
    "bleu": "max",
    "bleurt": "max",
    "cer": "min",
    "chrf": "min",
    "code_eval": "max",
    "comet": "max",
    "competition_math": "max",
    "coval": "max",
    "cuad": "max",
    "f1": "max",
    "gleu": "max",
    "google_bleu": "max",
    "matthews_correlation": "max",
    "meteor": "max",
    "pearsonr": "max",
    "precision": "max",
    "recall": "max",
    "rouge": "max",
    "sacrebleu": "max",
    "sari": "max",
    "seqeval": "max",
    "spearmanr": "max",
    "ter": "min",
    "wer": "min",
}
huggingface_submetric_to_metric = {"rouge1": "rouge", "rouge2": "rouge"}


def get_estimator_class(task, estimator_name):
    # when adding a new learner, need to add an elif branch
    if "xgboost" == estimator_name:
        estimator_class = (
            XGBoost_TS_Regressor if TS_FORECAST == task else XGBoostSklearnEstimator
        )
    elif "xgb_limitdepth" == estimator_name:
        estimator_class = (
            XGBoostLimitDepth_TS_Regressor
            if TS_FORECAST == task
            else XGBoostLimitDepthEstimator
        )
    elif "rf" == estimator_name:
        estimator_class = (
            RF_TS_Regressor if TS_FORECAST == task else RandomForestEstimator
        )
    elif "lgbm" == estimator_name:
        estimator_class = LGBM_TS_Regressor if TS_FORECAST == task else LGBMEstimator
    elif "lrl1" == estimator_name:
        estimator_class = LRL1Classifier
    elif "lrl2" == estimator_name:
        estimator_class = LRL2Classifier
    elif "catboost" == estimator_name:
        estimator_class = CatBoostEstimator
    elif "extra_tree" == estimator_name:
        estimator_class = (
            ExtraTrees_TS_Regressor if TS_FORECAST == task else ExtraTreesEstimator
        )
    elif "kneighbor" == estimator_name:
        estimator_class = KNeighborsEstimator
    elif "prophet" in estimator_name:
        estimator_class = Prophet
    elif estimator_name == "arima":
        estimator_class = ARIMA
    elif estimator_name == "sarimax":
        estimator_class = SARIMAX
    elif estimator_name == "transformer":
        estimator_class = TransformersEstimator
    else:
        raise ValueError(
            estimator_name + " is not a built-in learner. "
            "Please use AutoML.add_learner() to add a customized learner."
        )
    return estimator_class


def metric_loss_score(
    metric_name,
    y_predict,
    y_true,
    labels=None,
    sample_weight=None,
    groups=None,
):
    if is_in_sklearn_metric_name_set(metric_name):
        return sklearn_metric_loss_score(
            metric_name, y_predict, y_true, labels, sample_weight, groups
        )
    else:
        """
        hf's datasets.load_metric("pearsonr") returns nan (hf's bug), overwriting it here
        """
        if metric_name == "spearmanr":
            from scipy.stats import spearmanr

            y_true = y_true.to_list() if type(y_true) == pd.Series else list(y_true)
            score = spearmanr(list(y_predict), y_true)[0]
            metric_mode = "max"
        elif metric_name == "pearsonr":
            from scipy.stats import pearsonr

            y_true = y_true.to_list() if type(y_true) == pd.Series else list(y_true)
            score = pearsonr(list(y_predict), y_true)[0]
            metric_mode = "max"
        else:
            try:
                import datasets

                datasets_metric_name = huggingface_submetric_to_metric.get(
                    metric_name, metric_name
                )
                metric = datasets.load_metric(datasets_metric_name)
                metric_mode = huggingface_metric_to_mode[datasets_metric_name]

                if "rouge" in metric_name:
                    score = metric.compute(predictions=y_predict, references=y_true)[
                        metric_name
                    ].mid.fmeasure
                elif metric_name == "seqeval":
                    y_true = [
                        [x for x in each_y_true if x != -100] for each_y_true in y_true
                    ]
                    y_pred = [
                        y_predict[each_idx][: len(y_true[each_idx])]
                        for each_idx in range(len(y_predict))
                    ]
                    score = metric.compute(predictions=y_pred, references=y_true)[
                        "overall_accuracy"
                    ]
                else:
                    score = metric.compute(predictions=y_predict, references=y_true)[
                        metric_name
                    ]
            except ImportError:
                raise Exception(
                    metric_name
                    + " is not an built-in sklearn metric and nlp is not installed. "
                    "Currently built-in sklearn metrics are: "
                    "r2, rmse, mae, mse, accuracy, roc_auc, roc_auc_ovr, roc_auc_ovo,"
                    "log_loss, mape, f1, micro_f1, macro_f1, ap. "
                    "If the metric is an nlp metric, please pip install flaml[nlp] ",
                    "or pass a customized metric function to AutoML.fit(metric=func)",
                )
            # If the metric is not found from huggingface dataset metric list (i.e., FileNotFoundError)
            # ask the user to provide a custom metric
            except FileNotFoundError:
                raise Exception(
                    metric_name
                    + " is neither an sklearn metric nor a huggingface metric. "
                    "Currently built-in sklearn metrics are: "
                    "r2, rmse, mae, mse, accuracy, roc_auc, roc_auc_ovr, roc_auc_ovo,"
                    "log_loss, mape, f1, micro_f1, macro_f1, ap. "
                    "Currently built-in huggingface metrics are: "
                    + ", ".join(huggingface_metric_to_mode.keys())
                    + ". Please pass a customized metric function to AutoML.fit(metric=func)"
                )
        if metric_mode == "max":
            return 1 - score
        else:
            return score


def is_in_sklearn_metric_name_set(metric_name):
    return metric_name.startswith("ndcg") or metric_name in sklearn_metric_name_set


def sklearn_metric_loss_score(
    metric_name,
    y_predict,
    y_true,
    labels=None,
    sample_weight=None,
    groups=None,
):
    """Loss using the specified metric.

    Args:
        metric_name: A string of the metric name, one of
            'r2', 'rmse', 'mae', 'mse', 'accuracy', 'roc_auc', 'roc_auc_ovr',
            'roc_auc_ovo', 'log_loss', 'mape', 'f1', 'ap', 'ndcg',
            'micro_f1', 'macro_f1'.
        y_predict: A 1d or 2d numpy array of the predictions which can be
            used to calculate the metric. E.g., 2d for log_loss and 1d
            for others.
        y_true: A 1d numpy array of the true labels.
        labels: A 1d numpy array of the unique labels.
        sample_weight: A 1d numpy array of the sample weight.
        groups: A 1d numpy array of the group labels.

    Returns:
        score: A float number of the loss, the lower the better.
    """

    metric_name = metric_name.lower()

    if "r2" == metric_name:
        score = 1.0 - r2_score(y_true, y_predict, sample_weight=sample_weight)
    elif metric_name == "rmse":
        score = np.sqrt(
            mean_squared_error(y_true, y_predict, sample_weight=sample_weight)
        )
    elif metric_name == "mae":
        score = mean_absolute_error(y_true, y_predict, sample_weight=sample_weight)
    elif metric_name == "mse":
        score = mean_squared_error(y_true, y_predict, sample_weight=sample_weight)
    elif metric_name == "accuracy":
        score = 1.0 - accuracy_score(y_true, y_predict, sample_weight=sample_weight)
    elif metric_name == "roc_auc":
        score = 1.0 - roc_auc_score(y_true, y_predict, sample_weight=sample_weight)
    elif metric_name == "roc_auc_ovr":
        score = 1.0 - roc_auc_score(
            y_true, y_predict, sample_weight=sample_weight, multi_class="ovr"
        )
    elif metric_name == "roc_auc_ovo":
        score = 1.0 - roc_auc_score(
            y_true, y_predict, sample_weight=sample_weight, multi_class="ovo"
        )
    elif "log_loss" == metric_name:
        score = log_loss(y_true, y_predict, labels=labels, sample_weight=sample_weight)
    elif "mape" == metric_name:
        try:
            score = mean_absolute_percentage_error(y_true, y_predict)
        except ValueError:
            return np.inf
    elif "micro_f1" == metric_name:
        score = 1 - f1_score(
            y_true, y_predict, sample_weight=sample_weight, average="micro"
        )
    elif "macro_f1" == metric_name:
        score = 1 - f1_score(
            y_true, y_predict, sample_weight=sample_weight, average="macro"
        )
    elif "f1" == metric_name:
        score = 1 - f1_score(y_true, y_predict, sample_weight=sample_weight)
    elif "ap" == metric_name:
        score = 1 - average_precision_score(
            y_true, y_predict, sample_weight=sample_weight
        )
    elif "ndcg" in metric_name:
        if "@" in metric_name:
            k = int(metric_name.split("@", 1)[-1])
            counts = group_counts(groups)
            score = 0
            psum = 0
            for c in counts:
                score -= ndcg_score(
                    np.asarray([y_true[psum : psum + c]]),
                    np.asarray([y_predict[psum : psum + c]]),
                    k=k,
                )
                psum += c
            score /= len(counts)
            score += 1
        else:
            score = 1 - ndcg_score([y_true], [y_predict])
    return score


def get_y_pred(estimator, X, eval_metric, obj):
    if eval_metric in ["roc_auc", "ap"] and "binary" in obj:
        y_pred_classes = estimator.predict_proba(X)
        y_pred = y_pred_classes[:, 1] if y_pred_classes.ndim > 1 else y_pred_classes
    elif eval_metric in ["log_loss", "roc_auc", "roc_auc_ovr", "roc_auc_ovo"]:
        y_pred = estimator.predict_proba(X)
    else:
        y_pred = estimator.predict(X)
    return y_pred


def _eval_estimator(
    config,
    estimator,
    X_train,
    y_train,
    X_val,
    y_val,
    weight_val,
    groups_val,
    eval_metric,
    obj,
    labels=None,
    log_training_metric=False,
    fit_kwargs={},
):
    if isinstance(eval_metric, str):
        pred_start = time.time()
        val_pred_y = get_y_pred(estimator, X_val, eval_metric, obj)
        pred_time = (time.time() - pred_start) / X_val.shape[0]
        val_loss = metric_loss_score(
            eval_metric, val_pred_y, y_val, labels, weight_val, groups_val
        )
        metric_for_logging = {"pred_time": pred_time}
        if log_training_metric:
            train_pred_y = get_y_pred(estimator, X_train, eval_metric, obj)
            metric_for_logging["train_loss"] = metric_loss_score(
                eval_metric,
                train_pred_y,
                y_train,
                labels,
                fit_kwargs.get("sample_weight"),
                fit_kwargs.get("groups"),
            )
    else:  # customized metric function
        val_loss, metric_for_logging = eval_metric(
            X_val,
            y_val,
            estimator,
            labels,
            X_train,
            y_train,
            weight_val,
            fit_kwargs.get("sample_weight"),
            config,
            groups_val,
            fit_kwargs.get("groups"),
        )
        pred_time = metric_for_logging.get("pred_time", 0)
        val_pred_y = None
        # eval_metric may return val_pred_y but not necessarily. Setting None for now.
    return val_loss, metric_for_logging, pred_time, val_pred_y


def get_val_loss(
    config,
    estimator,
    X_train,
    y_train,
    X_val,
    y_val,
    weight_val,
    groups_val,
    eval_metric,
    obj,
    labels=None,
    budget=None,
    log_training_metric=False,
    fit_kwargs={},
):

    start = time.time()
    # if groups_val is not None:
    #     fit_kwargs['groups_val'] = groups_val
    #     fit_kwargs['X_val'] = X_val
    #     fit_kwargs['y_val'] = y_val
    estimator.fit(X_train, y_train, budget, **fit_kwargs)
    val_loss, metric_for_logging, pred_time, _ = _eval_estimator(
        config,
        estimator,
        X_train,
        y_train,
        X_val,
        y_val,
        weight_val,
        groups_val,
        eval_metric,
        obj,
        labels,
        log_training_metric,
        fit_kwargs,
    )
    if hasattr(estimator, "intermediate_results"):
        metric_for_logging["intermediate_results"] = estimator.intermediate_results
    train_time = time.time() - start
    return val_loss, metric_for_logging, train_time, pred_time


def evaluate_model_CV(
    config,
    estimator,
    X_train_all,
    y_train_all,
    budget,
    kf,
    task,
    eval_metric,
    best_val_loss,
    log_training_metric=False,
    fit_kwargs={},
):
    start_time = time.time()
    total_val_loss = 0
    total_metric = None
    metric = None
    train_time = pred_time = 0
    valid_fold_num = total_fold_num = 0
    n = kf.get_n_splits()
    X_train_split, y_train_split = X_train_all, y_train_all
    if task in CLASSIFICATION:
        labels = np.unique(y_train_all)
    else:
        labels = None
    groups = None
    shuffle = False if task == TS_FORECAST else True
    if isinstance(kf, RepeatedStratifiedKFold):
        kf = kf.split(X_train_split, y_train_split)
    elif isinstance(kf, GroupKFold):
        groups = kf.groups
        kf = kf.split(X_train_split, y_train_split, groups)
        shuffle = False
    elif isinstance(kf, TimeSeriesSplit):
        kf = kf.split(X_train_split, y_train_split)
    else:
        kf = kf.split(X_train_split)
    rng = np.random.RandomState(2020)
    val_loss_list = []
    budget_per_train = budget / n
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
            fit_kwargs["groups"] = groups[train_index]
            groups_val = groups[val_index]
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
            task,
            labels,
            budget_per_train,
            log_training_metric=log_training_metric,
            fit_kwargs=fit_kwargs,
        )
        if weight is not None:
            fit_kwargs["sample_weight"] = weight
        valid_fold_num += 1
        total_fold_num += 1
        total_val_loss += val_loss_i
        if log_training_metric or not isinstance(eval_metric, str):
            if isinstance(total_metric, dict):
                total_metric = {k: total_metric[k] + v for k, v in metric_i.items()}
            elif total_metric is not None:
                total_metric += metric_i
            else:
                total_metric = metric_i
        train_time += train_time_i
        pred_time += pred_time_i
        if valid_fold_num == n:
            val_loss_list.append(total_val_loss / valid_fold_num)
            total_val_loss = valid_fold_num = 0
        elif time.time() - start_time >= budget:
            val_loss_list.append(total_val_loss / valid_fold_num)
            break
    val_loss = np.max(val_loss_list)
    n = total_fold_num
    if log_training_metric or not isinstance(eval_metric, str):
        if isinstance(total_metric, dict):
            metric = {k: v / n for k, v in total_metric.items()}
        else:
            metric = total_metric / n
    pred_time /= n
    # budget -= time.time() - start_time
    # if val_loss < best_val_loss and budget > budget_per_train:
    #     estimator.cleanup()
    #     estimator.fit(X_train_all, y_train_all, budget, **fit_kwargs)
    return val_loss, metric, train_time, pred_time


def compute_estimator(
    X_train,
    y_train,
    X_val,
    y_val,
    weight_val,
    groups_val,
    budget,
    kf,
    config_dic,
    task,
    estimator_name,
    eval_method,
    eval_metric,
    best_val_loss=np.Inf,
    n_jobs=1,
    estimator_class=None,
    log_training_metric=False,
    fit_kwargs={},
):
    estimator_class = estimator_class or get_estimator_class(task, estimator_name)
    estimator = estimator_class(
        **config_dic,
        task=task,
        n_jobs=n_jobs,
    )
    if "holdout" == eval_method:
        val_loss, metric_for_logging, train_time, pred_time = get_val_loss(
            config_dic,
            estimator,
            X_train,
            y_train,
            X_val,
            y_val,
            weight_val,
            groups_val,
            eval_metric,
            task,
            budget=budget,
            log_training_metric=log_training_metric,
            fit_kwargs=fit_kwargs,
        )
    else:
        val_loss, metric_for_logging, train_time, pred_time = evaluate_model_CV(
            config_dic,
            estimator,
            X_train,
            y_train,
            budget,
            kf,
            task,
            eval_metric,
            best_val_loss,
            log_training_metric=log_training_metric,
            fit_kwargs=fit_kwargs,
        )
    return estimator, val_loss, metric_for_logging, train_time, pred_time


def train_estimator(
    config_dic,
    X_train,
    y_train,
    task,
    estimator_name,
    n_jobs=1,
    estimator_class=None,
    budget=None,
    fit_kwargs={},
):
    start_time = time.time()
    estimator_class = estimator_class or get_estimator_class(task, estimator_name)
    estimator = estimator_class(
        **config_dic,
        task=task,
        n_jobs=n_jobs,
    )
    if X_train is not None:
        train_time = estimator.fit(X_train, y_train, budget, **fit_kwargs)
    else:
        estimator = estimator.estimator_class(**estimator.params)
    train_time = time.time() - start_time
    return estimator, train_time


def get_classification_objective(num_labels: int) -> str:
    if num_labels == 2:
        objective_name = "binary"
    else:
        objective_name = "multi"
    return objective_name


def norm_confusion_matrix(y_true, y_pred):
    """normalized confusion matrix.

    Args:
        estimator: A multi-class classification estimator.
        y_true: A numpy array or a pandas series of true labels.
        y_pred: A numpy array or a pandas series of predicted labels.

    Returns:
        A normalized confusion matrix.
    """
    from sklearn.metrics import confusion_matrix

    conf_mat = confusion_matrix(y_true, y_pred)
    norm_conf_mat = conf_mat.astype("float") / conf_mat.sum(axis=1)[:, np.newaxis]
    return norm_conf_mat


def multi_class_curves(y_true, y_pred_proba, curve_func):
    """Binarize the data for multi-class tasks and produce ROC or precision-recall curves.

    Args:
        y_true: A numpy array or a pandas series of true labels.
        y_pred_proba: A numpy array or a pandas dataframe of predicted probabilites.
        curve_func: A function to produce a curve (e.g., roc_curve or precision_recall_curve).

    Returns:
        A tuple of two dictionaries with the same set of keys (class indices).
        The first dictionary curve_x stores the x coordinates of each curve, e.g.,
            curve_x[0] is an 1D array of the x coordinates of class 0.
        The second dictionary curve_y stores the y coordinates of each curve, e.g.,
            curve_y[0] is an 1D array of the y coordinates of class 0.
    """
    from sklearn.preprocessing import label_binarize

    classes = np.unique(y_true)
    y_true_binary = label_binarize(y_true, classes=classes)

    curve_x, curve_y = {}, {}
    for i in range(len(classes)):
        curve_x[i], curve_y[i], _ = curve_func(y_true_binary[:, i], y_pred_proba[:, i])
    return curve_x, curve_y
