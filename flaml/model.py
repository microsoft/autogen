'''!
 * Copyright (c) 2020 Microsoft Corporation. All rights reserved.
 * Licensed under the MIT License. 
'''

import numpy as np
import xgboost as xgb
from xgboost import XGBClassifier, XGBRegressor
import time
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from lightgbm import LGBMClassifier, LGBMRegressor
import scipy.sparse
import pandas as pd


class BaseEstimator:
    '''The abstract class for all learners

    Typical example:
        XGBoostEstimator: for regression
        XGBoostSklearnEstimator: for classification
        LGBMEstimator, RandomForestEstimator, LRL1Classifier, LRL2Classifier: 
            for both regression and classification        
    '''

    def __init__(self, objective_name = 'binary:logistic', 
        **params):
        '''Constructor
        
        Args:
            objective_name: A string of the objective name, one of
                'binary:logistic', 'multi:softmax', 'regression'
            n_jobs: An integer of the number of parallel threads
            params: A dictionary of the hyperparameter names and values
        '''
        self.params = params
        self.estimator_class = None
        self.objective_name = objective_name
        if '_estimator_type' in params:
            self._estimator_type = params['_estimator_type']
        else:
            self._estimator_type = "regressor" if objective_name=='regression' \
                else "classifier" 

    def get_params(self, deep=False):
        params = self.params.copy()
        params["objective_name"] = self.objective_name
        if hasattr(self, '_estimator_type'):
            params['_estimator_type'] = self._estimator_type
        return params

    @property
    def classes_(self):
        return self.model.classes_

    def preprocess(self, X):
        return X

    def _fit(self, X_train, y_train):    

        curent_time = time.time()
        X_train = self.preprocess(X_train)
        model = self.estimator_class(**self.params)
        model.fit(X_train, y_train)
        train_time =  time.time() - curent_time
        self.model = model
        return train_time

    def fit(self, X_train, y_train, budget=None):    
        '''Train the model from given training data
        
        Args:
            X_train: A numpy array of training data in shape n*m
            y_train: A numpy array of labels in shape n*1
            budget: A float of the time budget in seconds

        Returns:
            train_time: A float of the training time in seconds
        '''
        return self._fit(X_train, y_train)

    def predict(self, X_test):
        '''Predict label from features
        
        Args:
            X_test: A numpy array of featurized instances, shape n*m

        Returns:
            A numpy array of shape n*1. 
            Each element is the label for a instance
        '''      
        X_test = self.preprocess(X_test)
        return self.model.predict(X_test)

    def predict_proba(self, X_test):
        '''Predict the probability of each class from features

        Only works for classification problems

        Args:
            model: An object of trained model with method predict_proba()
            X_test: A numpy array of featurized instances, shape n*m

        Returns:
            A numpy array of shape n*c. c is the # classes
            Each element at (i,j) is the probability for instance i to be in
                class j
        '''
        if 'regression' in self.objective_name:
            print('Regression tasks do not support predict_prob')
            raise ValueError
        else:
            X_test = self.preprocess(X_test)
            return self.model.predict_proba(X_test)

    def cleanup(self): pass


class SKLearnEstimator(BaseEstimator):


    def preprocess(self, X):
        if isinstance(X, pd.DataFrame):
            X = X.copy()
            cat_columns = X.select_dtypes(include=['category']).columns
            X[cat_columns] = X[cat_columns].apply(lambda x: x.cat.codes)
        return X


class LGBMEstimator(BaseEstimator):


    def __init__(self, objective_name='binary:logistic', n_jobs=1,
     n_estimators=2, max_leaves=2, min_child_weight=1e-3, learning_rate=0.1, 
     subsample=1.0, reg_lambda=1.0, reg_alpha=0.0, colsample_bylevel=1.0, 
     colsample_bytree=1.0, log_max_bin=8, **params):
        super().__init__(objective_name, **params)
        # Default: ‘regression’ for LGBMRegressor, 
        # ‘binary’ or ‘multiclass’ for LGBMClassifier
        if 'regression' in objective_name:
            final_objective_name = 'regression'
        elif 'binary' in objective_name:
            final_objective_name = 'binary'
        elif 'multi' in objective_name:
            final_objective_name = 'multiclass'
        else:
            final_objective_name = 'regression'
        self.params = {
            "n_estimators": int(round(n_estimators)),
            "num_leaves":  params[
                'num_leaves'] if 'num_leaves' in params else int(
                    round(max_leaves)),
            'objective': params[
                "objective"] if "objective" in params else final_objective_name,
            'n_jobs': n_jobs,
            'learning_rate': float(learning_rate),
            'reg_alpha': float(reg_alpha),
            'reg_lambda': float(reg_lambda),
            'min_child_weight': float(min_child_weight),
            'colsample_bytree':float(colsample_bytree),
            'subsample': float(subsample),
        }
        self.params['max_bin'] = params['max_bin'] if 'max_bin' in params else (
            1<<int(round(log_max_bin)))-1
        if 'regression' in objective_name:
            self.estimator_class = LGBMRegressor
        else:
            self.estimator_class = LGBMClassifier
        self.time_per_iter = None
        self.train_size = 0

    def preprocess(self, X):
        if not isinstance(X, pd.DataFrame) and scipy.sparse.issparse(
            X) and np.issubdtype(X.dtype, np.integer):
            X = X.astype(float)
        return X

    def fit(self, X_train, y_train, budget=None):
        start_time = time.time()
        n_iter = self.params["n_estimators"]
        if (not self.time_per_iter or
         abs(self.train_size-X_train.shape[0])>4) and budget is not None:
            self.params["n_estimators"] = 1
            self.t1 = self._fit(X_train, y_train)
            if self.t1 >= budget: 
                self.params["n_estimators"] = n_iter
                return self.t1
            self.params["n_estimators"] = 4
            self.t2 = self._fit(X_train, y_train)
            self.time_per_iter = (self.t2 - self.t1)/(
                self.params["n_estimators"]-1) if self.t2 > self.t1 \
                else self.t1 if self.t1 else 0.001
            self.train_size = X_train.shape[0]
            if self.t1+self.t2>=budget or n_iter==self.params["n_estimators"]:
                self.params["n_estimators"] = n_iter
                return time.time() - start_time
        if budget is not None:
            self.params["n_estimators"] = min(n_iter, int((budget-time.time()+
                start_time-self.t1)/self.time_per_iter+1))
        if self.params["n_estimators"] > 0:
            self._fit(X_train, y_train)
        self.params["n_estimators"] = n_iter
        train_time = time.time() - start_time
        return train_time


class XGBoostEstimator(SKLearnEstimator):
    ''' not using sklearn API, used for regression '''


    def __init__(self, objective_name='regression', all_thread=False, n_jobs=1,
        n_estimators=4, max_leaves=4, subsample=1.0, min_child_weight=1, 
        learning_rate=0.1, reg_lambda=1.0, reg_alpha=0.0, colsample_bylevel=1.0,
        colsample_bytree=1.0, tree_method='auto', **params):
        super().__init__(objective_name, **params)
        self.n_estimators = int(round(n_estimators))
        self.max_leaves = int(round(max_leaves))
        self.grids = []
        self.params = {
            'max_leaves': int(round(max_leaves)),
            'max_depth': 0,
            'grow_policy': params[
                "grow_policy"] if "grow_policy" in params else 'lossguide',
            'tree_method':tree_method,
            'verbosity': 0,
            'nthread':n_jobs,
            'learning_rate': float(learning_rate),
            'subsample': float(subsample),
            'reg_alpha': float(reg_alpha),
            'reg_lambda': float(reg_lambda),
            'min_child_weight': float(min_child_weight),
            'booster': params['booster'] if 'booster' in params else 'gbtree',
            'colsample_bylevel': float(colsample_bylevel),
            'colsample_bytree':float(colsample_bytree),
            }
        if all_thread:
            del self.params['nthread']

    def get_params(self, deep=False):
        params = super().get_params()
        params["n_jobs"] = params['nthread']
        return params

    def fit(self, X_train, y_train, budget=None):    
        curent_time = time.time()        
        if not scipy.sparse.issparse(X_train):
            self.params['tree_method'] = 'hist'
            X_train = self.preprocess(X_train)
        dtrain = xgb.DMatrix(X_train, label=y_train)
        if self.max_leaves>0:
            xgb_model = xgb.train(self.params,  dtrain, self.n_estimators)
            del dtrain
            train_time = time.time() - curent_time
            self.model = xgb_model
            return train_time
        else:
            return None

    def predict(self, X_test):
        if not scipy.sparse.issparse(X_test):
            X_test = self.preprocess(X_test)
        dtest = xgb.DMatrix(X_test)
        return super().predict(dtest)


class XGBoostSklearnEstimator(SKLearnEstimator, LGBMEstimator):
    ''' using sklearn API, used for classification '''


    def __init__(self, objective_name='binary:logistic', n_jobs=1,  
        n_estimators=4, max_leaves=4, subsample=1.0, 
        min_child_weight=1, learning_rate=0.1, reg_lambda=1.0, reg_alpha=0.0,
        colsample_bylevel=1.0, colsample_bytree=1.0, tree_method='hist', 
        **params):
        super().__init__(objective_name, **params)
        self.params = {
        "n_estimators": int(round(n_estimators)),
        'max_leaves': int(round(max_leaves)),
        'max_depth': 0,
        'grow_policy': params[
                "grow_policy"] if "grow_policy" in params else 'lossguide',
        'tree_method':tree_method,
        'verbosity': 0,
        'n_jobs': n_jobs,
        'learning_rate': float(learning_rate),
        'subsample': float(subsample),
        'reg_alpha': float(reg_alpha),
        'reg_lambda': float(reg_lambda),
        'min_child_weight': float(min_child_weight),
        'booster': params['booster'] if 'booster' in params else 'gbtree',
        'colsample_bylevel': float(colsample_bylevel),
        'colsample_bytree': float(colsample_bytree),
        }

        if 'regression' in objective_name:
            self.estimator_class = XGBRegressor
        else:
            self.estimator_class = XGBClassifier
        self.time_per_iter = None
        self.train_size = 0

    def fit(self, X_train, y_train, budget=None):    
        if scipy.sparse.issparse(X_train):
            self.params['tree_method'] = 'auto'
        return super().fit(X_train, y_train, budget)
        

class RandomForestEstimator(SKLearnEstimator, LGBMEstimator):


    def __init__(self, objective_name = 'binary:logistic', n_jobs = 1,
      n_estimators = 4, max_leaves = 4, max_features = 1.0, 
      min_samples_split = 2, min_samples_leaf = 1, criterion = 1, **params):
        super().__init__(objective_name, **params)
        self.params = {
        "n_estimators": int(round(n_estimators)),
        "n_jobs": n_jobs,
        'max_features': float(max_features),
        }
        if 'regression' in objective_name:
            self.estimator_class = RandomForestRegressor
        else:
            self.estimator_class = RandomForestClassifier
            self.params['criterion'] = 'entropy' if criterion>1.5 else 'gini'
        self.time_per_iter = None
        self.train_size = 0

    def get_params(self, deep=False):
        params = super().get_params()
        params["criterion"] = 1 if params["criterion"]=='gini' else 2
        return params


class ExtraTreeEstimator(RandomForestEstimator):


    def __init__(self, objective_name = 'binary:logistic', n_jobs = 1,
      n_estimators = 4, max_leaves = 4, max_features = 1.0, 
      min_samples_split = 2, min_samples_leaf = 1, criterion = 1, **params):
        super().__init__(objective_name, **params)
        self.params = {
        "n_estimators": int(round(n_estimators)),
        "n_jobs": n_jobs,
        'max_features': float(max_features),
        }
        if 'regression' in objective_name:
            from sklearn.ensemble import ExtraTreesRegressor
            self.estimator_class = ExtraTreesRegressor
        else:
            from sklearn.ensemble import ExtraTreesClassifier
            self.estimator_class = ExtraTreesClassifier
            self.params['criterion'] = 'entropy' if criterion>1.5 else 'gini'
        self.time_per_iter = None
        self.train_size = 0


class LRL1Classifier(SKLearnEstimator):


    def __init__(self, tol=0.0001, C=1.0, 
        objective_name='binary:logistic', n_jobs=1, **params):
        super().__init__(objective_name, **params)
        self.params = {
            'penalty': 'l1',
            'tol': float(tol),
            'C': float(C),
            'solver': 'saga',
            'n_jobs': n_jobs,
        }
        if 'regression' in objective_name:
            self.estimator_class = None
            print('Does not support regression task')
            raise NotImplementedError
        else:
            self.estimator_class = LogisticRegression


class LRL2Classifier(SKLearnEstimator):


    def __init__(self, tol=0.0001, C=1.0, 
        objective_name='binary:logistic', n_jobs=1, **params):
        super().__init__(objective_name, **params)
        self.params = {
            'penalty': 'l2',
            'tol': float(tol),
            'C': float(C),
            'solver': 'lbfgs',
            'n_jobs': n_jobs,
        }
        if 'regression' in objective_name:
            self.estimator_class = None
            print('Does not support regression task')
            raise NotImplementedError
        else:
            self.estimator_class = LogisticRegression


class CatBoostEstimator(BaseEstimator):


    time_per_iter = None
    train_size = 0

    def __init__(self, objective_name = 'binary:logistic', n_jobs=1,
    n_estimators=8192, exp_max_depth=64, learning_rate=0.1, rounds=4, 
    l2_leaf_reg=3, **params):
        super().__init__(objective_name, **params)
        self.params = {
            "early_stopping_rounds": int(round(rounds)),
            "n_estimators": n_estimators, 
            'learning_rate': learning_rate,
            'thread_count': n_jobs,
            'verbose': False,
            'random_seed': params[
                "random_seed"] if "random_seed" in params else 10242048,
        }
        # print(n_estimators)
        if 'regression' in objective_name:
            from catboost import CatBoostRegressor
            self.estimator_class = CatBoostRegressor
        else:
            from catboost import CatBoostClassifier
            self.estimator_class = CatBoostClassifier

    def get_params(self, deep=False):
        params = super().get_params()
        params['n_jobs'] = params['thread_count']
        params['rounds'] = params['early_stopping_rounds']
        return params

    def fit(self, X_train, y_train, budget=None):
        start_time = time.time()
        n_iter = self.params["n_estimators"]
        if isinstance(X_train, pd.DataFrame):
            cat_features = list(X_train.select_dtypes(
                include='category').columns)
        else:
            cat_features = []
        if (not CatBoostEstimator.time_per_iter or
         abs(CatBoostEstimator.train_size-len(y_train))>4) and budget:
            # measure the time per iteration
            self.params["n_estimators"] = 1
            CatBoostEstimator.model = self.estimator_class(**self.params)
            CatBoostEstimator.model.fit(X_train, y_train,
             cat_features=cat_features)
            CatBoostEstimator.t1 = time.time() - start_time
            if CatBoostEstimator.t1 >= budget: 
                self.params["n_estimators"] = n_iter
                self.model = CatBoostEstimator.model
                return CatBoostEstimator.t1
            self.params["n_estimators"] = 4
            CatBoostEstimator.model = self.estimator_class(**self.params)
            CatBoostEstimator.model.fit(X_train, y_train,
             cat_features=cat_features)
            CatBoostEstimator.time_per_iter = (time.time() - start_time -
             CatBoostEstimator.t1)/(self.params["n_estimators"]-1)
            if CatBoostEstimator.time_per_iter <= 0: 
                CatBoostEstimator.time_per_iter = CatBoostEstimator.t1
            CatBoostEstimator.train_size = len(y_train)
            if time.time()-start_time>=budget or n_iter==self.params[
                "n_estimators"]: 
                self.params["n_estimators"] = n_iter
                self.model = CatBoostEstimator.model
                return time.time()-start_time
        if budget:
            train_times = 1 
            self.params["n_estimators"] = min(n_iter, int((budget-time.time()+
                start_time-CatBoostEstimator.t1)/train_times/
                CatBoostEstimator.time_per_iter+1))
            self.model = CatBoostEstimator.model
        if self.params["n_estimators"] > 0:
            l = max(int(len(y_train)*0.9), len(y_train)-1000)
            X_tr, y_tr = X_train[:l], y_train[:l]
            from catboost import Pool
            model = self.estimator_class(**self.params)
            model.fit(X_tr, y_tr, cat_features=cat_features, eval_set=Pool(
                data=X_train[l:], label=y_train[l:], cat_features=cat_features))
            # print(self.params["n_estimators"], model.get_best_iteration())
            self.model = model
        self.params["n_estimators"] = n_iter
        train_time = time.time() - start_time
        # print(budget, train_time)
        return train_time


class KNeighborsEstimator(BaseEstimator):

    
    def __init__(self, objective_name='binary:logistic', n_jobs=1,
     n_neighbors=5, **params):
        super().__init__(objective_name, **params)
        self.params= {
            'n_neighbors': int(round(n_neighbors)),
            'weights': 'distance',
            'n_jobs': n_jobs,
        }
        if 'regression' in objective_name:
            from sklearn.neighbors import KNeighborsRegressor
            self.estimator_class = KNeighborsRegressor
        else:
            from sklearn.neighbors import KNeighborsClassifier
            self.estimator_class = KNeighborsClassifier

    def preprocess(self, X):
        if isinstance(X, pd.DataFrame):
            cat_columns = X.select_dtypes(['category']).columns
            # print(X.dtypes)
            # print(cat_columns)
            if X.shape[1] == len(cat_columns):
                raise ValueError(
            "kneighbor requires at least one numeric feature")
            X = X.drop(cat_columns, axis=1) 
        return X
