'''!
 * Copyright (c) 2020-2021 Microsoft Corporation. All rights reserved.
 * Licensed under the MIT License.
'''

import time
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, r2_score, roc_auc_score, \
    accuracy_score, mean_absolute_error, log_loss, average_precision_score, \
    f1_score
from sklearn.model_selection import RepeatedStratifiedKFold
from .model import (
    XGBoostEstimator, XGBoostSklearnEstimator, RandomForestEstimator,
    LGBMEstimator, LRL1Classifier, LRL2Classifier, CatBoostEstimator,
    ExtraTreeEstimator, KNeighborsEstimator)

import logging
logger = logging.getLogger(__name__)


def get_estimator_class(task, estimator_name):
    ''' when adding a new learner, need to add an elif branch '''

    if 'xgboost' in estimator_name:
        if 'regression' in task:
            estimator_class = XGBoostEstimator
        else:
            estimator_class = XGBoostSklearnEstimator
    elif 'rf' in estimator_name:
        estimator_class = RandomForestEstimator
    elif 'lgbm' in estimator_name:
        estimator_class = LGBMEstimator
    elif 'lrl1' in estimator_name:
        estimator_class = LRL1Classifier
    elif 'lrl2' in estimator_name:
        estimator_class = LRL2Classifier
    elif 'catboost' in estimator_name:
        estimator_class = CatBoostEstimator
    elif 'extra_tree' in estimator_name:
        estimator_class = ExtraTreeEstimator
    elif 'kneighbor' in estimator_name:
        estimator_class = KNeighborsEstimator
    else:
        raise ValueError(
            estimator_name + ' is not a built-in learner. '
            'Please use AutoML.add_learner() to add a customized learner.')
    return estimator_class


def sklearn_metric_loss_score(
    metric_name, y_predict, y_true, labels=None, sample_weight=None
):
    '''Loss using the specified metric

    Args:
        metric_name: A string of the mtric name, one of
            'r2', 'rmse', 'mae', 'mse', 'accuracy', 'roc_auc', 'log_loss',
            'f1', 'ap'
        y_predict: A 1d or 2d numpy array of the predictions which can be
            used to calculate the metric. E.g., 2d for log_loss and 1d
            for others.
        y_true: A 1d numpy array of the true labels
        labels: A 1d numpy array of the unique labels
        sample_weight: A 1d numpy array of the sample weight

    Returns:
        score: A float number of the loss, the lower the better
    '''
    metric_name = metric_name.lower()
    if 'r2' in metric_name:
        score = 1.0 - r2_score(y_true, y_predict, sample_weight=sample_weight)
    elif metric_name == 'rmse':
        score = np.sqrt(mean_squared_error(
            y_true, y_predict, sample_weight=sample_weight))
    elif metric_name == 'mae':
        score = mean_absolute_error(
            y_true, y_predict, sample_weight=sample_weight)
    elif metric_name == 'mse':
        score = mean_squared_error(
            y_true, y_predict, sample_weight=sample_weight)
    elif metric_name == 'accuracy':
        score = 1.0 - accuracy_score(
            y_true, y_predict, sample_weight=sample_weight)
    elif 'roc_auc' in metric_name:
        score = 1.0 - roc_auc_score(
            y_true, y_predict, sample_weight=sample_weight)
    elif 'log_loss' in metric_name:
        score = log_loss(
            y_true, y_predict, labels=labels, sample_weight=sample_weight)
    elif 'f1' in metric_name:
        score = 1 - f1_score(y_true, y_predict, sample_weight=sample_weight)
    elif 'ap' in metric_name:
        score = 1 - average_precision_score(
            y_true, y_predict, sample_weight=sample_weight)
    else:
        raise ValueError(
            metric_name + ' is not a built-in metric, '
            'currently built-in metrics are: '
            'r2, rmse, mae, mse, accuracy, roc_auc, log_loss, f1, ap. '
            'please pass a customized metric function to AutoML.fit(metric=func)')
    return score


def get_y_pred(estimator, X, eval_metric, obj):
    if eval_metric in ['roc_auc', 'ap'] and 'binary' in obj:
        y_pred_classes = estimator.predict_proba(X)
        y_pred = y_pred_classes[
            :, 1] if y_pred_classes.ndim > 1 else y_pred_classes
    elif eval_metric in ['log_loss', 'roc_auc']:
        y_pred = estimator.predict_proba(X)
    else:
        y_pred = estimator.predict(X)
    return y_pred


def get_test_loss(
    estimator, X_train, y_train, X_test, y_test, weight_test,
    eval_metric, obj, labels=None, budget=None, train_loss=False, fit_kwargs={}
):
    start = time.time()
    train_time = estimator.fit(X_train, y_train, budget, **fit_kwargs)
    if isinstance(eval_metric, str):
        test_pred_y = get_y_pred(estimator, X_test, eval_metric, obj)
        test_loss = sklearn_metric_loss_score(eval_metric, test_pred_y, y_test,
                                              labels, weight_test)
        if train_loss is not False:
            test_pred_y = get_y_pred(estimator, X_train, eval_metric, obj)
            train_loss = sklearn_metric_loss_score(
                eval_metric, test_pred_y,
                y_train, labels, fit_kwargs.get('sample_weight'))
    else:  # customized metric function
        test_loss, train_loss = eval_metric(
            X_test, y_test, estimator, labels, X_train, y_train,
            weight_test, fit_kwargs.get('sample_weight'))
    train_time = time.time() - start
    return test_loss, train_time, train_loss


def train_model(estimator, X_train, y_train, budget, fit_kwargs={}):
    train_time = estimator.fit(X_train, y_train, budget, **fit_kwargs)
    return train_time


def evaluate_model(
    estimator, X_train, y_train, X_val, y_val, weight_val,
    budget, kf, task, eval_method, eval_metric, best_val_loss, train_loss=False,
    fit_kwargs={}
):
    if 'holdout' in eval_method:
        val_loss, train_loss, train_time = evaluate_model_holdout(
            estimator, X_train, y_train, X_val, y_val, weight_val, budget,
            task, eval_metric, best_val_loss, train_loss=train_loss,
            fit_kwargs=fit_kwargs)
    else:
        val_loss, train_loss, train_time = evaluate_model_CV(
            estimator, X_train, y_train, budget, kf, task,
            eval_metric, best_val_loss, train_loss=train_loss,
            fit_kwargs=fit_kwargs)
    return val_loss, train_loss, train_time


def evaluate_model_holdout(
    estimator, X_train, y_train, X_val, y_val,
    weight_val, budget, task, eval_metric, best_val_loss, train_loss=False,
    fit_kwargs={}
):
    val_loss, train_time, train_loss = get_test_loss(
        estimator, X_train, y_train, X_val, y_val, weight_val, eval_metric,
        task, budget=budget, train_loss=train_loss, fit_kwargs=fit_kwargs)
    return val_loss, train_loss, train_time


def evaluate_model_CV(
    estimator, X_train_all, y_train_all, budget, kf,
    task, eval_metric, best_val_loss, train_loss=False, fit_kwargs={}
):
    start_time = time.time()
    total_val_loss = total_train_loss = 0
    train_time = 0
    valid_fold_num = 0
    n = kf.get_n_splits()
    X_train_split, y_train_split = X_train_all, y_train_all
    if task == 'regression':
        labels = None
    else:
        labels = np.unique(y_train_all)

    if isinstance(kf, RepeatedStratifiedKFold):
        kf = kf.split(X_train_split, y_train_split)
    else:
        kf = kf.split(X_train_split)
    rng = np.random.RandomState(2020)
    val_loss_list = []
    budget_per_train = budget / (n + 1)
    if 'sample_weight' in fit_kwargs:
        weight = fit_kwargs['sample_weight']
        weight_val = None
    else:
        weight = weight_val = None
    for train_index, val_index in kf:
        train_index = rng.permutation(train_index)
        if isinstance(X_train_all, pd.DataFrame):
            X_train, X_val = X_train_split.iloc[
                train_index], X_train_split.iloc[val_index]
        else:
            X_train, X_val = X_train_split[
                train_index], X_train_split[val_index]
        if isinstance(y_train_all, pd.Series):
            y_train, y_val = y_train_split.iloc[
                train_index], y_train_split.iloc[val_index]
        else:
            y_train, y_val = y_train_split[
                train_index], y_train_split[val_index]
        estimator.cleanup()
        if weight is not None:
            fit_kwargs['sample_weight'], weight_val = weight[
                train_index], weight[val_index]
        val_loss_i, train_time_i, train_loss_i = get_test_loss(
            estimator, X_train, y_train, X_val, y_val, weight_val,
            eval_metric, task, labels, budget_per_train,
            train_loss=train_loss, fit_kwargs=fit_kwargs)
        if weight is not None:
            fit_kwargs['sample_weight'] = weight
        valid_fold_num += 1
        total_val_loss += val_loss_i
        if train_loss is not False:
            if total_train_loss != 0:
                total_train_loss += train_loss_i
            else:
                total_train_loss = train_loss_i
        train_time += train_time_i
        if valid_fold_num == n:
            val_loss_list.append(total_val_loss / valid_fold_num)
            total_val_loss = valid_fold_num = 0
        elif time.time() - start_time >= budget:
            val_loss_list.append(total_val_loss / valid_fold_num)
            break
    val_loss = np.max(val_loss_list)
    if train_loss is not False:
        train_loss = total_train_loss / n
    budget -= time.time() - start_time
    if val_loss < best_val_loss and budget > budget_per_train:
        estimator.cleanup()
        estimator.fit(X_train_all, y_train_all, budget, **fit_kwargs)
    return val_loss, train_loss, train_time


def compute_estimator(
    X_train, y_train, X_val, y_val, weight_val, budget, kf,
    config_dic, task, estimator_name, eval_method, eval_metric,
    best_val_loss=np.Inf, n_jobs=1, estimator_class=None, train_loss=False,
    fit_kwargs={}
):
    start_time = time.time()
    estimator_class = estimator_class or get_estimator_class(
        task, estimator_name)
    estimator = estimator_class(
        **config_dic, task=task, n_jobs=n_jobs)
    val_loss, train_loss, train_time = evaluate_model(
        estimator, X_train, y_train, X_val, y_val, weight_val, budget, kf, task,
        eval_method, eval_metric, best_val_loss, train_loss=train_loss,
        fit_kwargs=fit_kwargs)
    all_time = time.time() - start_time
    return estimator, val_loss, train_loss, train_time, all_time


def train_estimator(
    X_train, y_train, config_dic, task,
    estimator_name, n_jobs=1, estimator_class=None, budget=None, fit_kwargs={}
):
    start_time = time.time()
    estimator_class = estimator_class or get_estimator_class(
        task, estimator_name)
    estimator = estimator_class(**config_dic, task=task, n_jobs=n_jobs)
    if X_train is not None:
        train_time = train_model(
            estimator, X_train, y_train, budget, fit_kwargs)
    else:
        estimator = estimator.estimator_class(**estimator.params)
    train_time = time.time() - start_time
    return estimator, train_time


def get_classification_objective(num_labels: int) -> str:
    if num_labels == 2:
        objective_name = 'binary:logistic'
    else:
        objective_name = 'multi:softmax'
    return objective_name
