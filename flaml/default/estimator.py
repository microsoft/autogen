from functools import wraps
from flaml.automl.task.task import CLASSIFICATION
from .suggest import preprocess_and_suggest_hyperparams

DEFAULT_LOCATION = "default_location"


def flamlize_estimator(super_class, name: str, task: str, alternatives=None):
    """Enhance an estimator class with flaml's data-dependent default hyperparameter settings.

    Example:

    ```python
    import sklearn.ensemble as ensemble
    RandomForestRegressor = flamlize_estimator(
        ensemble.RandomForestRegressor, "rf", "regression"
    )
    ```

    Args:
        super_class: an scikit-learn compatible estimator class.
        name: a str of the estimator's name.
        task: a str of the task type.
        alternatives: (Optional) a list for alternative estimator names. For example,
            ```[("max_depth", 0, "xgboost")]``` means if the "max_depth" is set to 0
            in the constructor, then look for the learned defaults for estimator "xgboost".
    """

    class EstimatorClass(super_class):
        """**Enhanced with flaml's data-dependent default hyperparameter settings.**"""

        @wraps(super_class.__init__)
        def __init__(self, **params):
            if DEFAULT_LOCATION in params:
                self._default_location = params.pop(DEFAULT_LOCATION)
            else:
                self._default_location = None
            self._params = params
            super().__init__(**params)

        # @classmethod
        # @wraps(super_class._get_param_names)
        # def _get_param_names(cls):
        #     return super_class._get_param_names() if hasattr(super_class, "_get_param_names") else []

        def suggest_hyperparams(self, X, y):
            """Suggest hyperparameters.

            Example:

            ```python
            from flaml.default import LGBMRegressor

            estimator = LGBMRegressor()
            hyperparams, estimator_name, X_transformed, y_transformed = estimator.fit(X_train, y_train)
            print(hyperparams)
            ```

            Args:
                X: A dataframe of training data in shape n*m.
                y: A series of labels in shape n*1.

            Returns:
                hyperparams: A dict of the hyperparameter configurations.
                estimator_name: A str of the underlying estimator name, e.g., 'xgb_limitdepth'.
                X_transformed: the preprocessed X.
                y_transformed: the preprocessed y.
            """
            estimator_name = name
            if alternatives:
                for alternative in alternatives:
                    if self._params.get(alternative[0]) == alternative[1]:
                        estimator_name = alternative[2]
                        break
            estimator_name = (
                "choose_xgb"
                if (estimator_name == "xgb_limitdepth" and "max_depth" not in self._params)
                else estimator_name
            )
            (
                hyperparams,
                estimator_class,
                X_transformed,
                y_transformed,
                self._feature_transformer,
                self._label_transformer,
            ) = preprocess_and_suggest_hyperparams(task, X, y, estimator_name, self._default_location)
            assert estimator_class == super_class
            hyperparams.update(self._params)
            return hyperparams, estimator_name, X_transformed, y_transformed

        @wraps(super_class.fit)
        def fit(self, X, y, *args, **params):
            hyperparams, estimator_name, X, y_transformed = self.suggest_hyperparams(X, y)
            self.set_params(**hyperparams)
            if self._label_transformer and estimator_name in [
                "rf",
                "extra_tree",
                "xgboost",
                "xgb_limitdepth",
                "choose_xgb",
            ]:
                # rf and et have trouble in handling boolean labels; xgboost requires integer labels
                fitted = super().fit(X, y_transformed, *args, **params)
                # if hasattr(self, "_classes"):
                #     self._classes = self._label_transformer.classes_
                # else:
                self.classes_ = self._label_transformer.classes_
                if "xgb" not in estimator_name:
                    # rf and et would do inverse transform automatically; xgb doesn't
                    self._label_transformer = None
            else:
                # lgbm doesn't need label transformation except for non-str/num labels
                try:
                    fitted = super().fit(X, y, *args, **params)
                    self._label_transformer = None
                except ValueError:
                    # Unknown label type: 'unknown'
                    fitted = super().fit(X, y_transformed, *args, **params)
                    self._classes = self._label_transformer.classes_
            return fitted

        @wraps(super_class.predict)
        def predict(self, X, *args, **params):
            if name != "lgbm" or task not in CLASSIFICATION:
                X = self._feature_transformer.transform(X)
            y_pred = super().predict(X, *args, **params)
            if self._label_transformer and y_pred.ndim == 1:
                y_pred = self._label_transformer.inverse_transform(y_pred)
            return y_pred

        if hasattr(super_class, "predict_proba"):

            @wraps(super_class.predict_proba)
            def predict_proba(self, X, *args, **params):
                X_test = self._feature_transformer.transform(X)
                y_pred = super().predict_proba(X_test, *args, **params)
                return y_pred

    EstimatorClass.__doc__ += " " + super_class.__doc__
    EstimatorClass.__name__ = super_class.__name__
    return EstimatorClass


try:
    import sklearn.ensemble as ensemble
except ImportError:
    RandomForestClassifier = RandomForestRegressor = ExtraTreesClassifier = ExtraTreesRegressor = ImportError(
        "Using flaml.default.* requires scikit-learn."
    )
else:
    RandomForestRegressor = flamlize_estimator(ensemble.RandomForestRegressor, "rf", "regression")
    RandomForestClassifier = flamlize_estimator(ensemble.RandomForestClassifier, "rf", "classification")
    ExtraTreesRegressor = flamlize_estimator(ensemble.ExtraTreesRegressor, "extra_tree", "regression")
    ExtraTreesClassifier = flamlize_estimator(ensemble.ExtraTreesClassifier, "extra_tree", "classification")

try:
    import lightgbm
except ImportError:
    LGBMRegressor = LGBMClassifier = ImportError("Using flaml.default.LGBM* requires lightgbm.")
else:
    LGBMRegressor = flamlize_estimator(lightgbm.LGBMRegressor, "lgbm", "regression")
    LGBMClassifier = flamlize_estimator(lightgbm.LGBMClassifier, "lgbm", "classification")

try:
    import xgboost
except ImportError:
    XGBClassifier = XGBRegressor = ImportError("Using flaml.default.XGB* requires xgboost.")
else:
    XGBRegressor = flamlize_estimator(
        xgboost.XGBRegressor,
        "xgb_limitdepth",
        "regression",
        [("max_depth", 0, "xgboost")],
    )
    XGBClassifier = flamlize_estimator(
        xgboost.XGBClassifier,
        "xgb_limitdepth",
        "classification",
        [("max_depth", 0, "xgboost")],
    )
    # if hasattr(xgboost.XGBRegressor, "_get_param_names"):
    #     XGBRegressor._get_param_names = xgboost.XGBRegressor._get_param_names
    #     XGBClassifier._get_param_names = xgboost.XGBClassifier._get_param_names
