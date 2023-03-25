import os
import sys
import warnings
import pytest
import sklearn.datasets as skds
from flaml import AutoML
from flaml.tune.spark.utils import check_spark

warnings.simplefilter(action="ignore")
if sys.platform == "darwin" or "nt" in os.name:
    # skip this test if the platform is not linux
    skip_spark = True
else:
    try:
        import pyspark
        from pyspark.ml.feature import VectorAssembler
        from flaml.automl.spark.utils import to_pandas_on_spark

        spark = (
            pyspark.sql.SparkSession.builder.appName("MyApp")
            .master("local[1]")
            .config(
                "spark.jars.packages",
                f"com.microsoft.azure:synapseml_2.12:0.10.2,org.apache.hadoop:hadoop-azure:{pyspark.__version__},com.microsoft.azure:azure-storage:8.6.6",
            )
            .config("spark.jars.repositories", "https://mmlspark.azureedge.net/maven")
            .config("spark.sql.debug.maxToStringFields", "100")
            .config("spark.driver.extraJavaOptions", "-Xss1m")
            .config("spark.executor.extraJavaOptions", "-Xss1m")
            .getOrCreate()
        )
        # spark.sparkContext.setLogLevel("ERROR")
        spark_available, _ = check_spark()
        skip_spark = not spark_available
    except ImportError:
        skip_spark = True


pytestmark = pytest.mark.skipif(
    skip_spark, reason="Spark is not installed. Skip all spark tests."
)


def _test_spark_synapseml_lightgbm(spark=None, task="classification"):
    if task == "classification":
        metric = "accuracy"
        X_train, y_train = skds.load_iris(return_X_y=True, as_frame=True)
    elif task == "regression":
        metric = "r2"
        X_train, y_train = skds.load_diabetes(return_X_y=True, as_frame=True)
    elif task == "rank":
        metric = "ndcg@5"
        sdf = spark.read.format("parquet").load(
            "wasbs://publicwasb@mmlspark.blob.core.windows.net/lightGBMRanker_test.parquet"
        )
        df = to_pandas_on_spark(sdf)
        X_train = df.drop(["labels"], axis=1)
        y_train = df["labels"]

    automl_experiment = AutoML()
    automl_settings = {
        "time_budget": 10,
        "metric": metric,
        "task": task,
        "estimator_list": ["lgbm_spark"],
        "log_training_metric": True,
        "log_file_name": "test_spark_synapseml.log",
        "model_history": True,
        "verbose": 5,
    }

    y_train.name = "label"
    X_train = to_pandas_on_spark(X_train)
    y_train = to_pandas_on_spark(y_train)

    if task == "rank":
        automl_settings["groupCol"] = "query"
        automl_settings["evalAt"] = [1, 3, 5]
        automl_settings["groups"] = X_train["query"]
        automl_settings["groups"].name = "groups"
        X_train = X_train.to_spark(index_col="index")
    else:
        columns = X_train.columns
        feature_cols = [col for col in columns if col != "label"]
        featurizer = VectorAssembler(inputCols=feature_cols, outputCol="features")
        X_train = featurizer.transform(X_train.to_spark(index_col="index"))[
            "index", "features"
        ]
    X_train = to_pandas_on_spark(X_train)

    automl_experiment.fit(X_train=X_train, y_train=y_train, **automl_settings)
    if task == "classification":
        print(automl_experiment.classes_)
    print(automl_experiment.model)
    print(automl_experiment.config_history)
    print(automl_experiment.best_model_for_estimator("lgbm_spark"))
    print(automl_experiment.best_iteration)
    print(automl_experiment.best_estimator)
    print(automl_experiment.best_loss)
    if task != "rank":
        print(automl_experiment.score(X_train, y_train, metric=metric))
    del automl_settings["metric"]
    del automl_settings["model_history"]
    del automl_settings["log_training_metric"]
    del automl_settings["verbose"]
    del automl_settings["estimator_list"]
    automl_experiment = AutoML(task=task)
    try:
        duration = automl_experiment.retrain_from_log(
            X_train=X_train,
            y_train=y_train,
            train_full=True,
            record_id=0,
            **automl_settings,
        )
        print(duration)
        print(automl_experiment.model)
        print(automl_experiment.predict(X_train)[:5])
        print(y_train.to_numpy()[:5])
    except ValueError:
        return


def test_spark_synapseml_classification():
    _test_spark_synapseml_lightgbm(spark, "classification")


def test_spark_synapseml_regression():
    _test_spark_synapseml_lightgbm(spark, "regression")


def test_spark_synapseml_rank():
    _test_spark_synapseml_lightgbm(spark, "rank")


def test_spark_input_df():
    df = (
        spark.read.format("csv")
        .option("header", True)
        .option("inferSchema", True)
        .load(
            "wasbs://publicwasb@mmlspark.blob.core.windows.net/company_bankruptcy_prediction_data.csv"
        )
    )
    train, test = df.randomSplit([0.8, 0.2], seed=1)
    feature_cols = df.columns[1:]
    featurizer = VectorAssembler(inputCols=feature_cols, outputCol="features")
    train_data = featurizer.transform(train)["Bankrupt?", "features"]
    test_data = featurizer.transform(test)["Bankrupt?", "features"]
    automl = AutoML()
    settings = {
        "time_budget": 30,  # total running time in seconds
        "metric": "roc_auc",
        "estimator_list": [
            "lgbm_spark"
        ],  # list of ML learners; we tune lightgbm in this example
        "task": "classification",  # task type
        "log_file_name": "flaml_experiment.log",  # flaml log file
        "seed": 7654321,  # random seed
    }
    df = to_pandas_on_spark(to_pandas_on_spark(train_data).to_spark(index_col="index"))

    automl.fit(
        dataframe=df,
        label="Bankrupt?",
        labelCol="Bankrupt?",
        isUnbalance=True,
        **settings,
    )

    try:
        model = automl.model.estimator
        predictions = model.transform(test_data)

        from synapse.ml.train import ComputeModelStatistics

        metrics = ComputeModelStatistics(
            evaluationMetric="classification",
            labelCol="Bankrupt?",
            scoredLabelsCol="prediction",
        ).transform(predictions)
        metrics.show()
    except AttributeError:
        print("No fitted model because of too short training time.")

    # test invalid params
    settings = {
        "time_budget": 10,  # total running time in seconds
        "metric": "roc_auc",
        "estimator_list": [
            "lgbm"
        ],  # list of ML learners; we tune lightgbm in this example
        "task": "classification",  # task type
    }
    with pytest.raises(ValueError) as excinfo:
        automl.fit(
            dataframe=df,
            label="Bankrupt?",
            labelCol="Bankrupt?",
            isUnbalance=True,
            **settings,
        )
    assert "No estimator is left." in str(excinfo.value)


if __name__ == "__main__":
    test_spark_synapseml_classification()
    test_spark_synapseml_regression()
    test_spark_synapseml_rank()
    test_spark_input_df()

    # import cProfile
    # import pstats
    # from pstats import SortKey

    # cProfile.run("test_spark_input_df()", "test_spark_input_df.profile")
    # p = pstats.Stats("test_spark_input_df.profile")
    # p.strip_dirs().sort_stats(SortKey.CUMULATIVE).print_stats("utils.py")
