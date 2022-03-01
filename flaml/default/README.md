# FLAML-Zero: Zero-shot AutoML

## Zero-shot AutoML

There are several ways to use zero-shot AutoML, i.e., train a model with the data-dependent default configuration.

0. Use estimators in `flaml.default.estimator`.

```python
from flaml.default import LGBMRegressor

estimator = LGBMRegressor()
estimator.fit(X_train, y_train)
estimator.predict(X_test, y_test)
```


1. Use AutoML.fit(). set `starting_points="data"` and `max_iter=0`.

```python
X_train, y_train = load_iris(return_X_y=True, as_frame=as_frame)
automl = AutoML()
automl_settings = {
    "time_budget": 2,
    "task": "classification",
    "log_file_name": "test/iris.log",
    "starting_points": "data",
    "max_iter": 0,
}
automl.fit(X_train, y_train, **automl_settings)
```

2. Use `flaml.default.preprocess_and_suggest_hyperparams`.

```python
from flaml.default import preprocess_and_suggest_hyperparams

X, y = load_iris(return_X_y=True, as_frame=True)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.33, random_state=42)
hyperparams, estimator_class, X_transformed, y_transformed, feature_transformer, label_transformer = preprocess_and_suggest_hyperparams(
    "classification", X_train, y_train, "lgbm"
)
model = estimator_class(**hyperparams)  # estimator_class is LGBMClassifier
model.fit(X_transformed, y_train)  # LGBMClassifier can handle raw labels
X_test = feature_transformer.transform(X_test)  # preprocess test data
y_pred = model.predict(X_test)
```

If you want to use your own meta-learned defaults, specify the path containing the meta-learned defaults. For example,

```python
X_train, y_train = load_iris(return_X_y=True, as_frame=as_frame)
automl = AutoML()
automl_settings = {
    "time_budget": 2,
    "task": "classification",
    "log_file_name": "test/iris.log",
    "starting_points": "data:test/default",
    "estimator_list": ["lgbm", "xgb_limitdepth", "rf"]
    "max_iter": 0,
}
automl.fit(X_train, y_train, **automl_settings)
```

Since this is a multiclass task, it will look for the following files under `test/default/`:

- `all/multiclass.json`.
- `{learner_name}/multiclass.json` for every learner_name in the estimator_list.

Read the next subsection to understand how to generate these files if you would like to meta-learn the defaults yourself.

To perform hyperparameter search starting with the data-dependent defaults, remove `max_iter=0`.

## Perform Meta Learning

FLAML provides a package `flaml.default` to learn defaults customized for your own tasks/learners/metrics.

### Prepare a collection of training tasks

Collect a diverse set of training tasks. For each task, extract its meta feature and save in a .csv file. For example, test/default/all/metafeatures.csv:

```
Dataset,NumberOfInstances,NumberOfFeatures,NumberOfClasses,PercentageOfNumericFeatures
2dplanes,36691,10,0,1.0
adult,43957,14,2,0.42857142857142855
Airlines,485444,7,2,0.42857142857142855
Albert,382716,78,2,0.3333333333333333
Amazon_employee_access,29492,9,2,0.0
bng_breastTumor,104976,9,0,0.1111111111111111
bng_pbc,900000,18,0,0.5555555555555556
car,1555,6,4,0.0
connect-4,60801,42,3,0.0
dilbert,9000,2000,5,1.0
Dionis,374569,60,355,1.0
poker,922509,10,0,1.0
```

The first column is the dataset name, and the latter four are meta features.

### Prepare the candidate configurations

You can extract the best configurations for each task in your collection of training tasks by running flaml on each of them with a long enough budget. Save the best configuration in a .json file under `{location_for_defaults}/{learner_name}/{task_name}.json`. For example,

```python
X_train, y_train = load_iris(return_X_y=True, as_frame=as_frame)
automl.fit(X_train, y_train, estimator_list=["lgbm"], **settings)
automl.save_best_config("test/default/lgbm/iris.json")
```

### Evaluate each candidate configuration on each task

Save the evaluation results in a .csv file. For example, save the evaluation results for lgbm under `test/default/lgbm/results.csv`:

```
task,fold,type,result,params
2dplanes,0,regression,0.946366,{'_modeljson': 'lgbm/2dplanes.json'}
2dplanes,0,regression,0.907774,{'_modeljson': 'lgbm/adult.json'}
2dplanes,0,regression,0.901643,{'_modeljson': 'lgbm/Airlines.json'}
2dplanes,0,regression,0.915098,{'_modeljson': 'lgbm/Albert.json'}
2dplanes,0,regression,0.302328,{'_modeljson': 'lgbm/Amazon_employee_access.json'}
2dplanes,0,regression,0.94523,{'_modeljson': 'lgbm/bng_breastTumor.json'}
2dplanes,0,regression,0.945698,{'_modeljson': 'lgbm/bng_pbc.json'}
2dplanes,0,regression,0.946194,{'_modeljson': 'lgbm/car.json'}
2dplanes,0,regression,0.945549,{'_modeljson': 'lgbm/connect-4.json'}
2dplanes,0,regression,0.946232,{'_modeljson': 'lgbm/default.json'}
2dplanes,0,regression,0.945594,{'_modeljson': 'lgbm/dilbert.json'}
2dplanes,0,regression,0.836996,{'_modeljson': 'lgbm/Dionis.json'}
2dplanes,0,regression,0.917152,{'_modeljson': 'lgbm/poker.json'}
adult,0,binary,0.927203,{'_modeljson': 'lgbm/2dplanes.json'}
adult,0,binary,0.932072,{'_modeljson': 'lgbm/adult.json'}
adult,0,binary,0.926563,{'_modeljson': 'lgbm/Airlines.json'}
adult,0,binary,0.928604,{'_modeljson': 'lgbm/Albert.json'}
adult,0,binary,0.911171,{'_modeljson': 'lgbm/Amazon_employee_access.json'}
adult,0,binary,0.930645,{'_modeljson': 'lgbm/bng_breastTumor.json'}
adult,0,binary,0.928603,{'_modeljson': 'lgbm/bng_pbc.json'}
adult,0,binary,0.915825,{'_modeljson': 'lgbm/car.json'}
adult,0,binary,0.919499,{'_modeljson': 'lgbm/connect-4.json'}
adult,0,binary,0.930109,{'_modeljson': 'lgbm/default.json'}
adult,0,binary,0.932453,{'_modeljson': 'lgbm/dilbert.json'}
adult,0,binary,0.921959,{'_modeljson': 'lgbm/Dionis.json'}
adult,0,binary,0.910763,{'_modeljson': 'lgbm/poker.json'}
...
```

The `type` column indicates the type of the task, such as regression, binary or multiclass.
The `result` column stores the evaluation result, assuming the large the better. The `params` column indicates which json config is used. For example 'lgbm/2dplanes.json' indicates that the best lgbm configuration extracted from 2dplanes is used.

### Learn data-dependent defaults

To recap, the inputs required for meta-learning are:

1. Metafeatures: e.g., `{location}/all/metafeatures.csv`.
1. Configurations: `{location}/{learner_name}/{task_name}.json`.
1. Evaluation results: `{location}/{learner_name}/results.csv`.

For example, if the input location is "test/default", learners are lgbm, xgb_limitdepth and rf, the following command learns data-dependent defaults for binary classification tasks.

```bash
python portfolio.py --output test/default --input test/default --metafeatures test/default/all/metafeatures.csv --task binary --estimator lgbm xgb_limitdepth rf
```

It will produce the following files as output:

- test/default/lgbm/binary.json: the learned defaults for lgbm.
- test/default/xgb_limitdepth/binary.json: the learned defaults for xgb_limitdepth.
- test/default/rf/binary.json: the learned defaults for rf.
- test/default/all/binary.json: the learned defaults for lgbm, xgb_limitdepth and rf together.

Change "binary" into "multiclass" or "regression" for the other tasks.

## Reference

For more technical details, please check our research paper.

* [Mining Robust Default Configurations for Resource-constrained AutoML](https://arxiv.org/abs/2202.09927). Moe Kayali, Chi Wang. arXiv preprint arXiv:2202.09927 (2022).

```bibtex
@article{Kayali2022default,
    title={Mining Robust Default Configurations for Resource-constrained AutoML},
    author={Moe Kayali and Chi Wang},
    year={2022},
    journal={arXiv preprint arXiv:2202.09927},
}
```