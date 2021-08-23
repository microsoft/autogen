from openml.exceptions import OpenMLServerException


def test_automl(budget=5, dataset_format='dataframe'):
    from flaml.data import load_openml_dataset
    try:
        X_train, X_test, y_train, y_test = load_openml_dataset(
            dataset_id=1169, data_dir='test/', dataset_format=dataset_format)
    except OpenMLServerException:
        print("OpenMLServerException raised")
        return
    ''' import AutoML class from flaml package '''
    from flaml import AutoML
    automl = AutoML()
    settings = {
        "time_budget": budget,  # total running time in seconds
        "metric": 'accuracy',  # primary metrics can be chosen from: ['accuracy','roc_auc','roc_auc_ovr','roc_auc_ovo','f1','log_loss','mae','mse','r2']
        "task": 'classification',  # task type
        "log_file_name": 'airlines_experiment.log',  # flaml log file
        "seed": 7654321,    # random seed
    }
    '''The main flaml automl API'''
    automl.fit(X_train=X_train, y_train=y_train, **settings)
    ''' retrieve best config and best learner'''
    print('Best ML leaner:', automl.best_estimator)
    print('Best hyperparmeter config:', automl.best_config)
    print('Best accuracy on validation data: {0:.4g}'.format(1 - automl.best_loss))
    print('Training duration of best run: {0:.4g} s'.format(automl.best_config_train_time))
    print(automl.model.estimator)
    ''' pickle and save the automl object '''
    import pickle
    with open('automl.pkl', 'wb') as f:
        pickle.dump(automl, f, pickle.HIGHEST_PROTOCOL)
    ''' compute predictions of testing dataset '''
    y_pred = automl.predict(X_test)
    print('Predicted labels', y_pred)
    print('True labels', y_test)
    y_pred_proba = automl.predict_proba(X_test)[:, 1]
    ''' compute different metric values on testing dataset'''
    from flaml.ml import sklearn_metric_loss_score
    print('accuracy', '=', 1 - sklearn_metric_loss_score('accuracy', y_pred, y_test))
    print('roc_auc', '=', 1 - sklearn_metric_loss_score('roc_auc', y_pred_proba, y_test))
    print('log_loss', '=', sklearn_metric_loss_score('log_loss', y_pred_proba, y_test))
    from flaml.data import get_output_from_log
    time_history, best_valid_loss_history, valid_loss_history, config_history, train_loss_history = \
        get_output_from_log(filename=settings['log_file_name'], time_budget=60)
    for config in config_history:
        print(config)
    print(automl.prune_attr)
    print(automl.max_resource)
    print(automl.min_resource)


def test_automl_array():
    test_automl(5, 'array')


def test_mlflow():
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mlflow"])
    import mlflow
    from flaml.data import load_openml_task
    try:
        X_train, X_test, y_train, y_test = load_openml_task(
            task_id=7592, data_dir='test/')
    except OpenMLServerException:
        print("OpenMLServerException raised")
        return
    ''' import AutoML class from flaml package '''
    from flaml import AutoML
    automl = AutoML()
    settings = {
        "time_budget": 5,  # total running time in seconds
        "metric": 'accuracy',  # primary metrics can be chosen from: ['accuracy','roc_auc','roc_auc_ovr','roc_auc_ovo','f1','log_loss','mae','mse','r2']
        "estimator_list": ['lgbm', 'rf', 'xgboost'],  # list of ML learners
        "task": 'classification',  # task type
        "sample": False,  # whether to subsample training data
        "log_file_name": 'adult.log',  # flaml log file
    }
    mlflow.set_experiment("flaml")
    with mlflow.start_run():
        '''The main flaml automl API'''
        automl.fit(X_train=X_train, y_train=y_train, **settings)
    # subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "mlflow"])


if __name__ == "__main__":
    test_automl(300)
