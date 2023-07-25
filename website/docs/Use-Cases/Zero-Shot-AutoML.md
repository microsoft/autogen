# Zero Shot AutoML

`flaml.default` is a package for zero-shot AutoML, or "no-tuning" AutoML. It uses [`flaml.AutoML`](/docs/reference/automl/automl#automl-objects) and [`flaml.default.portfolio`](/docs/reference/default/portfolio) to mine good hyperparameter configurations across different datasets offline, and recommend data-dependent default configurations at runtime without expensive tuning.

Zero-shot AutoML has several benefits:
* The computation cost is just training one model. No tuning is involved.
* The decision of hyperparameter configuration is instant. No overhead to worry about.
* Your code remains the same. No breaking of the existing workflow.
* It requires less input from the user. No need to specify a tuning budget etc.
* All training data are used for, guess what, training. No need to worry about holding a subset of training data for validation (and overfitting the validation data).
* The offline preparation can be customized for a domain and leverage the historical tuning data. No experience is wasted.

## How to Use at Runtime

The easiest way to leverage this technique is to import a "flamlized" learner of your favorite choice and use it just as how you use the learner before. The automation is done behind the scene and you are not required to change your code. For example, if you are currently using:

```python
from lightgbm import LGBMRegressor

estimator = LGBMRegressor()
estimator.fit(X_train, y_train)
estimator.predict(X_test)
```

Simply replace the first line with:

```python
from flaml.default import LGBMRegressor
```

All the other code remains the same. And you are expected to get a equal or better model in most cases.

The current list of "flamlized" learners are:
* LGBMClassifier, LGBMRegressor.
* XGBClassifier, XGBRegressor.
* RandomForestClassifier, RandomForestRegressor.
* ExtraTreesClassifier, ExtraTreesRegressor.

### What's the magic behind the scene?

`flaml.default.LGBMRegressor` inherits `lightgbm.LGBMRegressor`, so all the APIs in `lightgbm.LGBMRegressor` are still valid in `flaml.default.LGBMRegressor`. The difference is, `flaml.default.LGBMRegressor` decides the hyperparameter configurations based on the training data. It would use a different configuration if it is predicted to outperform the original data-independent default. If you inspect the params of the fitted estimator, you can find what configuration is used. If the original default configuration is used, then it is equivalent to the original estimator.

The recommendation of which configuration should be used is based on offline AutoML run results. Information about the training dataset, such as the size of the dataset will be used to recommend a data-dependent configuration. The recommendation is done instantly in negligible time. The training can be faster or slower than using the original default configuration depending on the recommended configuration. Note that there is no tuning involved. Only one model is trained.

### Can I check the configuration before training?

Yes. You can use `suggest_hyperparams()` to find the suggested configuration. For example,

```python
from flaml.default import LGBMRegressor

estimator = LGBMRegressor()
hyperparams, estimator_name, X_transformed, y_transformed = estimator.suggest_hyperparams(X_train, y_train)
print(hyperparams)
```

If you would like more control over the training, use an equivalent, open-box way for zero-shot AutoML. For example,

```python
from flaml.default import preprocess_and_suggest_hyperparams

X, y = load_iris(return_X_y=True, as_frame=True)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.33, random_state=42)
hyperparams, estimator_class, X_transformed, y_transformed, feature_transformer, label_transformer = preprocess_and_suggest_hyperparams(
    "classification", X_train, y_train, "lgbm"
)
model = estimator_class(**hyperparams)  # estimator_class is lightgbm.LGBMClassifier
model.fit(X_transformed, y_train)  # LGBMClassifier can handle raw labels
X_test = feature_transformer.transform(X_test)  # preprocess test data
y_pred = model.predict(X_test)
```

Note that some classifiers like XGBClassifier require the labels to be integers, while others do not. So you can decide whether to use the transformed labels `y_transformed` and the label transformer `label_transformer`.
Also, each estimator may require specific preprocessing of the data. `X_transformed` is the preprocessed data, and `feature_transformer` is the preprocessor. It needs to be applied to the test data before prediction. These are automated when you use the "flamlized" learner. When you use the open-box way, pay attention to them.

### Combine zero shot AutoML and hyperparameter tuning

Zero Shot AutoML is fast. If tuning from the recommended data-dependent configuration is required, you can use `flaml.AutoML.fit()` and set `starting_points="data"`. For example,

```python
from flaml import AutoML
automl = AutoML()
automl_settings = {
    "task": "classification",
    "starting_points": "data",
    "estimator_list": ["lgbm"],
    "time_budget": 600,
    "max_iter": 50,
}
automl.fit(X_train, y_train, **automl_settings)
```

Note that if you set `max_iter=0` and `time_budget=None`, you are effectively using zero-shot AutoML. When `estimator_list` is omitted, the estimator together with its hyperparameter configuration will be decided in a zero-shot manner.

### Use your own meta-learned defaults

To use your own meta-learned defaults, specify the path containing the meta-learned defaults. For example,

```python
estimator = flaml.default.LGBMRegressor(default_location="location_for_defaults")
```

Or,

```python
preprocess_and_suggest_hyperparams(
    "classification", X_train, y_train, "lgbm", location="location_for_defaults"
)
```

Or,

```python
X_train, y_train = load_iris(return_X_y=True, as_frame=as_frame)
automl = AutoML()
automl_settings = {
    "task": "classification",
    "log_file_name": "test/iris.log",
    "starting_points": "data:location_for_defaults",
    "estimator_list": ["lgbm", "xgb_limitdepth", "rf"]
    "max_iter": 0,
}
automl.fit(X_train, y_train, **automl_settings)
```

Since this is a multiclass task, it will look for the following files under `{location_for_defaults}/`:

- `all/multiclass.json`.
- `{learner_name}/multiclass.json` for every learner_name in the estimator_list.

Read the next section to understand how to generate these files if you would like to meta-learn the defaults yourself.

## How to Prepare Offline

This section is intended for:
1. AutoML providers for a particular domain.
1. Data scientists or engineers who need to repeatedly train models for similar tasks with varying training data.

Instead of running full hyperparameter tuning from scratch every time, one can leverage the tuning experiences in similar tasks before. While we have offered the meta-learned defaults from tuning experiences of several popular learners on benchmark datasets for classification and regression, you can customize the defaults for your own tasks/learners/metrics based on your own tuning experiences.

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
The `result` column stores the evaluation result, assumed the large the better. The `params` column indicates which json config is used. For example 'lgbm/2dplanes.json' indicates that the best lgbm configuration extracted from 2dplanes is used.
Different types of tasks can appear in the same file, as long as any json config file can be used in all the tasks. For example, 'lgbm/2dplanes.json' is extracted from a regression task, and it can be applied to binary and multiclass tasks as well.

### Learn data-dependent defaults

To recap, the inputs required for meta-learning are:

1. Metafeatures: e.g., `{location}/all/metafeatures.csv`.
1. Configurations: `{location}/{learner_name}/{task_name}.json`.
1. Evaluation results: `{location}/{learner_name}/results.csv`.

For example, if the input location is "test/default", learners are lgbm, xgb_limitdepth and rf, the following command learns data-dependent defaults for binary classification tasks.

```bash
python portfolio.py --output test/default --input test/default --metafeatures test/default/all/metafeatures.csv --task binary --estimator lgbm xgb_limitdepth rf
```

In a few seconds, it will produce the following files as output:

- test/default/lgbm/binary.json: the learned defaults for lgbm.
- test/default/xgb_limitdepth/binary.json: the learned defaults for xgb_limitdepth.
- test/default/rf/binary.json: the learned defaults for rf.
- test/default/all/binary.json: the learned defaults for lgbm, xgb_limitdepth and rf together.

Change "binary" into "multiclass" or "regression", or your own types in your "results.csv" for the other types of tasks. To update the learned defaults when more experiences are available, simply update your input files and rerun the learning command.

### "Flamlize" a learner

You have now effectively built your own zero-shot AutoML solution. Congratulations!

Optionally, you can "flamlize" a learner using [`flaml.default.flamlize_estimator`](/docs/reference/default/estimator#flamlize_estimator) for easy dissemination. For example,

```python
import sklearn.ensemble as ensemble
from flaml.default import flamlize_estimator

ExtraTreesClassifier = flamlize_estimator(
    ensemble.ExtraTreesClassifier, "extra_tree", "classification"
)
```

Then, you can share this "flamlized" `ExtraTreesClassifier` together with the location of your learned defaults with others (or the _future_ yourself). They will benefit from your past experience. Your group can also share experiences in a central place and update the learned defaults continuously. Over time, your organization gets better collectively.
