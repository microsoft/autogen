# Integrate - Spark

FLAML has integrated Spark for distributed training. There are two main aspects of integration with Spark:
- Use Spark ML estimators for AutoML.
- Use Spark to run training in parallel spark jobs.

## Spark ML Estimators

FLAML integrates estimators based on Spark ML models. These models are trained in parallel using Spark, so we called them Spark estimators. To use these models, you first need to organize your data in the required format.

### Data

For Spark estimators, AutoML only consumes Spark data. FLAML provides a convenient function `to_pandas_on_spark` in the `flaml.automl.spark.utils` module to convert your data into a pandas-on-spark (`pyspark.pandas`) dataframe/series, which Spark estimators require.

This utility function takes data in the form of a `pandas.Dataframe` or `pyspark.sql.Dataframe` and converts it into a pandas-on-spark dataframe. It also takes `pandas.Series` or `pyspark.sql.Dataframe` and converts it into a [pandas-on-spark](https://spark.apache.org/docs/latest/api/python/user_guide/pandas_on_spark/index.html) series. If you pass in a `pyspark.pandas.Dataframe`, it will not make any changes.

This function also accepts optional arguments `index_col` and `default_index_type`.
- `index_col` is the column name to use as the index, default is None.
- `default_index_type` is the default index type, default is "distributed-sequence". More info about default index type could be found on Spark official [documentation](https://spark.apache.org/docs/latest/api/python/user_guide/pandas_on_spark/options.html#default-index-type)

Here is an example code snippet for Spark Data:

```python
import pandas as pd
from flaml.automl.spark.utils import to_pandas_on_spark
# Creating a dictionary
data = {"Square_Feet": [800, 1200, 1800, 1500, 850],
      "Age_Years": [20, 15, 10, 7, 25],
      "Price": [100000, 200000, 300000, 240000, 120000]}

# Creating a pandas DataFrame
dataframe = pd.DataFrame(data)
label = "Price"

# Convert to pandas-on-spark dataframe
psdf = to_pandas_on_spark(dataframe)
```

To use Spark ML models you need to format your data appropriately. Specifically, use [`VectorAssembler`](https://spark.apache.org/docs/latest/api/python/reference/api/pyspark.ml.feature.VectorAssembler.html) to merge all feature columns into a single vector column.

Here is an example of how to use it:
```python
from pyspark.ml.feature import VectorAssembler
columns = psdf.columns
feature_cols = [col for col in columns if col != label]
featurizer = VectorAssembler(inputCols=feature_cols, outputCol="features")
psdf = featurizer.transform(psdf.to_spark(index_col="index"))["index", "features"]
```

Later in conducting the experiment, use your pandas-on-spark data like non-spark data and pass them using `X_train, y_train` or `dataframe, label`.

### Estimators
#### Model List
- `lgbm_spark`: The class for fine-tuning Spark version LightGBM models, using [SynapseML](https://microsoft.github.io/SynapseML/docs/features/lightgbm/about/) API.

#### Usage
First, prepare your data in the required format as described in the previous section.

By including the models you intend to try in the `estimators_list` argument to `flaml.automl`, FLAML will start trying configurations for these models. If your input is Spark data, FLAML will also use estimators with the `_spark` postfix by default, even if you haven't specified them.

Here is an example code snippet using SparkML models in AutoML:

```python
import flaml
# prepare your data in pandas-on-spark format as we previously mentioned

automl = flaml.AutoML()
settings = {
    "time_budget": 30,
    "metric": "r2",
    "estimator_list": ["lgbm_spark"],  # this setting is optional
    "task": "regression",
}

automl.fit(
    dataframe=psdf,
    label=label,
    **settings,
)
```


[Link to notebook](https://github.com/microsoft/FLAML/blob/main/notebook/automl_bankrupt_synapseml.ipynb) | [Open in colab](https://colab.research.google.com/github/microsoft/FLAML/blob/main/notebook/automl_bankrupt_synapseml.ipynb)

## Parallel Spark Jobs
You can activate Spark as the parallel backend during parallel tuning in both [AutoML](/docs/Use-Cases/Task-Oriented-AutoML#parallel-tuning) and [Hyperparameter Tuning](/docs/Use-Cases/Tune-User-Defined-Function#parallel-tuning), by setting the `use_spark` to `true`. FLAML will dispatch your job to the distributed Spark backend using [`joblib-spark`](https://github.com/joblib/joblib-spark).

Please note that you should not set `use_spark` to `true` when applying AutoML and Tuning for Spark Data. This is because only SparkML models will be used for Spark Data in AutoML and Tuning. As SparkML models run in parallel, there is no need to distribute them with `use_spark` again.

All the Spark-related arguments are stated below. These arguments are available in both Hyperparameter Tuning and AutoML:


- `use_spark`: boolean, default=False | Whether to use spark to run the training in parallel spark jobs. This can be used to accelerate training on large models and large datasets, but will incur more overhead in time and thus slow down training in some cases. GPU training is not supported yet when use_spark is True. For Spark clusters, by default, we will launch one trial per executor. However, sometimes we want to launch more trials than the number of executors (e.g., local mode). In this case, we can set the environment variable `FLAML_MAX_CONCURRENT` to override the detected `num_executors`. The final number of concurrent trials will be the minimum of `n_concurrent_trials` and `num_executors`.
- `n_concurrent_trials`: int, default=1 | The number of concurrent trials. When n_concurrent_trials > 1, FLAML performes parallel tuning.
- `force_cancel`: boolean, default=False | Whether to forcely cancel Spark jobs if the search time exceeded the time budget. Spark jobs include parallel tuning jobs and Spark-based model training jobs.

An example code snippet for using parallel Spark jobs:
```python
import flaml
automl_experiment = flaml.AutoML()
automl_settings = {
    "time_budget": 30,
    "metric": "r2",
    "task": "regression",
    "n_concurrent_trials": 2,
    "use_spark": True,
    "force_cancel": True, # Activating the force_cancel option can immediately halt Spark jobs once they exceed the allocated time_budget.
}

automl.fit(
    dataframe=dataframe,
    label=label,
    **automl_settings,
)
```


[Link to notebook](https://github.com/microsoft/FLAML/blob/main/notebook/integrate_spark.ipynb) | [Open in colab](https://colab.research.google.com/github/microsoft/FLAML/blob/main/notebook/integrate_spark.ipynb)
