'''!
 * Copyright (c) 2020-2021 Microsoft Corporation. All rights reserved.
 * Licensed under the MIT License.
'''

import numpy as np
from scipy.sparse import vstack, issparse
import pandas as pd
from .training_log import training_log_reader

from datetime import datetime


def load_openml_dataset(dataset_id, data_dir=None, random_state=0):
    '''Load dataset from open ML.

    If the file is not cached locally, download it from open ML.

    Args:
        dataset_id: An integer of the dataset id in openml
        data_dir: A string of the path to store and load the data
        random_state: An integer of the random seed for splitting data

    Returns:
        X_train: A 2d numpy array of training data
        X_test:  A 2d numpy array of test data
        y_train: A 1d numpy arrya of labels for training data
        y_test:  A 1d numpy arrya of labels for test data
    '''
    import os
    import openml
    import pickle
    from sklearn.model_selection import train_test_split

    filename = 'openml_ds' + str(dataset_id) + '.pkl'
    filepath = os.path.join(data_dir, filename)
    if os.path.isfile(filepath):
        print('load dataset from', filepath)
        with open(filepath, 'rb') as f:
            dataset = pickle.load(f)
    else:
        print('download dataset from openml')
        dataset = openml.datasets.get_dataset(dataset_id)
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        with open(filepath, 'wb') as f:
            pickle.dump(dataset, f, pickle.HIGHEST_PROTOCOL)
    print('Dataset name:', dataset.name)
    X, y, * \
        __ = dataset.get_data(
            target=dataset.default_target_attribute, dataset_format='array')
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, random_state=random_state)
    print(
        'X_train.shape: {}, y_train.shape: {};\nX_test.shape: {}, y_test.shape: {}'.format(
            X_train.shape, y_train.shape, X_test.shape, y_test.shape,
        )
    )
    return X_train, X_test, y_train, y_test


def load_openml_task(task_id, data_dir):
    '''Load task from open ML.

    Use the first fold of the task.
    If the file is not cached locally, download it from open ML.

    Args:
        task_id: An integer of the task id in openml
        data_dir: A string of the path to store and load the data

    Returns:
        X_train: A 2d numpy array of training data
        X_test:  A 2d numpy array of test data
        y_train: A 1d numpy arrya of labels for training data
        y_test:  A 1d numpy arrya of labels for test data
    '''
    import os
    import openml
    import pickle
    task = openml.tasks.get_task(task_id)
    filename = 'openml_task' + str(task_id) + '.pkl'
    filepath = os.path.join(data_dir, filename)
    if os.path.isfile(filepath):
        print('load dataset from', filepath)
        with open(filepath, 'rb') as f:
            dataset = pickle.load(f)
    else:
        print('download dataset from openml')
        dataset = task.get_dataset()
        with open(filepath, 'wb') as f:
            pickle.dump(dataset, f, pickle.HIGHEST_PROTOCOL)
    X, y, _, _ = dataset.get_data(task.target_name, dataset_format='array')
    train_indices, test_indices = task.get_train_test_split_indices(
        repeat=0,
        fold=0,
        sample=0,
    )
    X_train = X[train_indices]
    y_train = y[train_indices]
    X_test = X[test_indices]
    y_test = y[test_indices]
    print(
        'X_train.shape: {}, y_train.shape: {},\nX_test.shape: {}, y_test.shape: {}'.format(
            X_train.shape, y_train.shape, X_test.shape, y_test.shape,
        )
    )
    return X_train, X_test, y_train, y_test


def get_output_from_log(filename, time_budget):
    '''Get output from log file

    Args:
        filename: A string of the log file name
        time_budget: A float of the time budget in seconds

    Returns:
        training_time_list: A list of the finished time of each logged iter
        best_error_list:
            A list of the best validation error after each logged iter
        error_list: A list of the validation error of each logged iter
        config_list:
            A list of the estimator, sample size and config of each logged iter
        logged_metric_list: A list of the logged metric of each logged iter
    '''

    best_config = None
    best_learner = None
    best_val_loss = float('+inf')
    training_duration = 0.0

    training_time_list = []
    config_list = []
    best_error_list = []
    error_list = []
    logged_metric_list = []
    best_config_list = []
    with training_log_reader(filename) as reader:
        for record in reader.records():
            time_used = record.total_search_time
            training_duration = time_used
            val_loss = record.validation_loss
            config = record.config
            learner = record.learner.split('_')[0]
            sample_size = record.sample_size
            train_loss = record.logged_metric

            if time_used < time_budget:
                if val_loss < best_val_loss:
                    best_val_loss = val_loss
                    best_config = config
                    best_learner = learner
                    best_config_list.append(best_config)
                training_time_list.append(training_duration)
                best_error_list.append(best_val_loss)
                logged_metric_list.append(train_loss)
                error_list.append(val_loss)
                config_list.append({"Current Learner": learner,
                                    "Current Sample": sample_size,
                                    "Current Hyper-parameters": record.config,
                                    "Best Learner": best_learner,
                                    "Best Hyper-parameters": best_config})

    return (training_time_list, best_error_list, error_list, config_list,
            logged_metric_list)


def concat(X1, X2):
    '''concatenate two matrices vertically
    '''
    if isinstance(X1, pd.DataFrame) or isinstance(X1, pd.Series):
        df = pd.concat([X1, X2], sort=False)
        df.reset_index(drop=True, inplace=True)
        if isinstance(X1, pd.DataFrame):
            cat_columns = X1.select_dtypes(
                include='category').columns
            if len(cat_columns):
                df[cat_columns] = df[cat_columns].astype('category')
        return df
    if issparse(X1):
        return vstack((X1, X2))
    else:
        return np.concatenate([X1, X2])


class DataTransformer:
    '''transform X, y
    '''

    def fit_transform(self, X, y, task):
        if isinstance(X, pd.DataFrame):
            X = X.copy()
            n = X.shape[0]
            cat_columns, num_columns, datetime_columns = [], [], []
            drop = False
            for column in X.columns:
                # sklearn\utils\validation.py needs int/float values
                if X[column].dtype.name == 'datetime64[ns]':
                    X[column] = X[column].map(datetime.toordinal)
                    datetime_columns.append(column)
                if X[column].dtype.name in ('object', 'category'):
                    if X[column].nunique() == 1 or X[column].nunique(
                            dropna=True) == n - X[column].isnull().sum():
                        X.drop(columns=column, inplace=True)
                        drop = True
                    elif X[column].dtype.name == 'category':
                        current_categories = X[column].cat.categories
                        if '__NAN__' not in current_categories:
                            X[column] = X[column].cat.add_categories(
                                '__NAN__').fillna('__NAN__')
                        cat_columns.append(column)
                    else:
                        X[column] = X[column].fillna('__NAN__')
                        cat_columns.append(column)
                else:
                    if X[column].nunique(dropna=True) < 2:
                        X.drop(columns=column, inplace=True)
                        drop = True
                    else:
                        X[column] = X[column].fillna(np.nan)
                        num_columns.append(column)
            X = X[cat_columns + num_columns]
            if cat_columns:
                X[cat_columns] = X[cat_columns].astype('category')
            if num_columns:
                X_num = X[num_columns]
                if drop and np.issubdtype(X_num.columns.dtype, np.integer):
                    X_num.columns = range(X_num.shape[1])
                else:
                    drop = False
                from sklearn.impute import SimpleImputer
                from sklearn.compose import ColumnTransformer
                self.transformer = ColumnTransformer([(
                    'continuous',
                    SimpleImputer(missing_values=np.nan, strategy='median'),
                    X_num.columns)])
                X[num_columns] = self.transformer.fit_transform(X_num)
            self._cat_columns, self._num_columns, self._datetime_columns = \
                cat_columns, num_columns, datetime_columns
            self._drop = drop

        if task == 'regression':
            self.label_transformer = None
        else:
            from sklearn.preprocessing import LabelEncoder
            self.label_transformer = LabelEncoder()
            y = self.label_transformer.fit_transform(y)
        return X, y

    def transform(self, X):
        if isinstance(X, pd.DataFrame):
            cat_columns, num_columns, datetime_columns = \
                self._cat_columns, self._num_columns, self._datetime_columns
            if datetime_columns:
                for dt_column in datetime_columns:
                    X[dt_column] = X[dt_column].map(datetime.toordinal)
            X = X[cat_columns + num_columns].copy()
            for column in cat_columns:
                # print(column, X[column].dtype.name)
                if X[column].dtype.name == 'object':
                    X[column] = X[column].fillna('__NAN__')
                elif X[column].dtype.name == 'category':
                    current_categories = X[column].cat.categories
                    if '__NAN__' not in current_categories:
                        X[column] = X[column].cat.add_categories(
                            '__NAN__').fillna('__NAN__')
            if cat_columns:
                X[cat_columns] = X[cat_columns].astype('category')
            if num_columns:
                X_num = X[num_columns].fillna(np.nan)
                if self._drop:
                    X_num.columns = range(X_num.shape[1])
                X[num_columns] = self.transformer.transform(X_num)
        return X
