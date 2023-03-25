import numpy as np
import pandas as pd
from functools import partial
from timeit import timeit
import pytest
import os

try:
    os.environ["PYARROW_IGNORE_TIMEZONE"] = "1"
    from pyspark.sql import SparkSession
    import pyspark
    import pyspark.pandas as ps
    from flaml.tune.spark.utils import (
        with_parameters,
        check_spark,
        get_n_cpus,
        get_broadcast_data,
    )
    from flaml.automl.spark.utils import (
        to_pandas_on_spark,
        train_test_split_pyspark,
        unique_pandas_on_spark,
        len_labels,
        unique_value_first_index,
        iloc_pandas_on_spark,
    )
    from flaml.automl.spark.metrics import spark_metric_loss_score
    from flaml.automl.ml import sklearn_metric_loss_score
    from pyspark.ml.linalg import Vectors

    spark_available, _ = check_spark()
    skip_spark = not spark_available
except ImportError:
    print("Spark is not installed. Skip all spark tests.")
    skip_spark = True

pytestmark = pytest.mark.skipif(
    skip_spark, reason="Spark is not installed. Skip all spark tests."
)


def test_with_parameters_spark():
    def train(config, data=None):
        if isinstance(data, pyspark.broadcast.Broadcast):
            data = data.value
        print(config, len(data))

    data = ["a"] * 10**6

    with_parameters_train = with_parameters(train, data=data)
    partial_train = partial(train, data=data)

    spark = SparkSession.builder.getOrCreate()
    rdd = spark.sparkContext.parallelize(list(range(2)))

    t_partial = timeit(
        lambda: rdd.map(lambda x: partial_train(config=x)).collect(), number=5
    )
    print("python_partial_train: " + str(t_partial))

    t_spark = timeit(
        lambda: rdd.map(lambda x: with_parameters_train(config=x)).collect(),
        number=5,
    )
    print("spark_with_parameters_train: " + str(t_spark))

    # assert t_spark < t_partial


def test_get_n_cpus_spark():
    n_cpus = get_n_cpus()
    assert isinstance(n_cpus, int)


def test_broadcast_code():
    from flaml.tune.spark.utils import broadcast_code
    from flaml.automl.model import LGBMEstimator

    custom_code = """
    from flaml.automl.model import LGBMEstimator
    from flaml import tune

    class MyLargeLGBM(LGBMEstimator):
        @classmethod
        def search_space(cls, **params):
            return {
                "n_estimators": {
                    "domain": tune.lograndint(lower=4, upper=32768),
                    "init_value": 32768,
                    "low_cost_init_value": 4,
                },
                "num_leaves": {
                    "domain": tune.lograndint(lower=4, upper=32768),
                    "init_value": 32768,
                    "low_cost_init_value": 4,
                },
            }
    """

    _ = broadcast_code(custom_code=custom_code)
    from flaml.tune.spark.mylearner import MyLargeLGBM

    assert isinstance(MyLargeLGBM(), LGBMEstimator)


def test_get_broadcast_data():
    data = ["a"] * 10
    spark = SparkSession.builder.getOrCreate()
    bc_data = spark.sparkContext.broadcast(data)
    assert get_broadcast_data(bc_data) == data


def test_to_pandas_on_spark(capsys):
    pdf = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    psdf = to_pandas_on_spark(pdf)
    print(psdf)
    captured = capsys.readouterr()
    assert captured.out == "   a  b\n0  1  4\n1  2  5\n2  3  6\n"
    assert isinstance(psdf, ps.DataFrame)

    spark = SparkSession.builder.getOrCreate()
    sdf = spark.createDataFrame(pdf)
    psdf = to_pandas_on_spark(sdf)
    print(psdf)
    captured = capsys.readouterr()
    assert captured.out == "   a  b\n0  1  4\n1  2  5\n2  3  6\n"
    assert isinstance(psdf, ps.DataFrame)

    pds = pd.Series([1, 2, 3])
    pss = to_pandas_on_spark(pds)
    print(pss)
    captured = capsys.readouterr()
    assert captured.out == "0    1\n1    2\n2    3\ndtype: int64\n"
    assert isinstance(pss, ps.Series)


def test_train_test_split_pyspark():
    pdf = pd.DataFrame({"x": [1, 2, 3, 4], "y": [0, 1, 1, 0]})
    spark = SparkSession.builder.getOrCreate()
    sdf = spark.createDataFrame(pdf).repartition(1)
    psdf = to_pandas_on_spark(sdf).spark.repartition(1)
    train_sdf, test_sdf = train_test_split_pyspark(
        sdf, test_fraction=0.5, to_pandas_spark=False, seed=1
    )
    train_psdf, test_psdf = train_test_split_pyspark(
        psdf, test_fraction=0.5, stratify_column="y", seed=1
    )
    assert isinstance(train_sdf, pyspark.sql.dataframe.DataFrame)
    assert isinstance(test_sdf, pyspark.sql.dataframe.DataFrame)
    assert isinstance(train_psdf, ps.DataFrame)
    assert isinstance(test_psdf, ps.DataFrame)
    assert train_sdf.count() == 2
    assert train_psdf.shape[0] == 2
    print(train_sdf.toPandas())
    print(test_sdf.toPandas())
    print(train_psdf.to_pandas())
    print(test_psdf.to_pandas())


def test_unique_pandas_on_spark():
    pdf = pd.DataFrame({"x": [1, 2, 2, 3], "y": [0, 1, 1, 0]})
    spark = SparkSession.builder.getOrCreate()
    sdf = spark.createDataFrame(pdf)
    psdf = to_pandas_on_spark(sdf)
    label_set, counts = unique_pandas_on_spark(psdf)
    assert np.array_equal(label_set, np.array([2, 1, 3]))
    assert np.array_equal(counts, np.array([2, 1, 1]))


def test_len_labels():
    y1 = np.array([1, 2, 5, 4, 5])
    y2 = ps.Series([1, 2, 5, 4, 5])
    assert len_labels(y1) == 4
    ll, la = len_labels(y2, return_labels=True)
    assert ll == 4
    assert set(la.to_numpy()) == set([1, 2, 5, 4])


def test_unique_value_first_index():
    y1 = np.array([1, 2, 5, 4, 5])
    y2 = ps.Series([1, 2, 5, 4, 5])
    l1, f1 = unique_value_first_index(y1)
    l2, f2 = unique_value_first_index(y2)
    assert np.array_equal(l1, np.array([1, 2, 4, 5]))
    assert np.array_equal(f1, np.array([0, 1, 3, 2]))
    assert np.array_equal(l2, np.array([1, 2, 5, 4]))
    assert np.array_equal(f2, np.array([0, 1, 2, 3]))


def test_n_current_trials():
    spark = SparkSession.builder.getOrCreate()
    sc = spark._jsc.sc()
    num_executors = (
        len([executor.host() for executor in sc.statusTracker().getExecutorInfos()]) - 1
    )

    def get_n_current_trials(n_concurrent_trials=0, num_executors=num_executors):
        try:
            FLAML_MAX_CONCURRENT = int(os.getenv("FLAML_MAX_CONCURRENT", 0))
            num_executors = max(num_executors, FLAML_MAX_CONCURRENT, 1)
        except ValueError:
            FLAML_MAX_CONCURRENT = 0
        max_spark_parallelism = (
            min(spark.sparkContext.defaultParallelism, FLAML_MAX_CONCURRENT)
            if FLAML_MAX_CONCURRENT > 0
            else spark.sparkContext.defaultParallelism
        )
        max_concurrent = max(1, max_spark_parallelism)
        n_concurrent_trials = min(
            n_concurrent_trials if n_concurrent_trials > 0 else num_executors,
            max_concurrent,
        )
        print("n_concurrent_trials:", n_concurrent_trials)
        return n_concurrent_trials

    os.environ["FLAML_MAX_CONCURRENT"] = "invlaid"
    assert get_n_current_trials() == num_executors
    os.environ["FLAML_MAX_CONCURRENT"] = "0"
    assert get_n_current_trials() == max(num_executors, 1)
    os.environ["FLAML_MAX_CONCURRENT"] = "4"
    tmp_max = min(4, spark.sparkContext.defaultParallelism)
    assert get_n_current_trials() == tmp_max
    os.environ["FLAML_MAX_CONCURRENT"] = "9999999"
    assert get_n_current_trials() == spark.sparkContext.defaultParallelism
    os.environ["FLAML_MAX_CONCURRENT"] = "100"
    tmp_max = min(100, spark.sparkContext.defaultParallelism)
    assert get_n_current_trials(1) == 1
    assert get_n_current_trials(2) == min(2, tmp_max)
    assert get_n_current_trials(50) == min(50, tmp_max)
    assert get_n_current_trials(200) == min(200, tmp_max)


def test_iloc_pandas_on_spark():
    psdf = ps.DataFrame({"x": [1, 2, 2, 3], "y": [0, 1, 1, 0]}, index=[0, 1, 2, 3])
    psds = ps.Series([1, 2, 2, 3], index=[0, 1, 2, 3])
    assert iloc_pandas_on_spark(psdf, 0).tolist() == [1, 0]
    d1 = iloc_pandas_on_spark(psdf, slice(1, 3)).to_pandas()
    d2 = pd.DataFrame({"x": [2, 2], "y": [1, 1]}, index=[1, 2])
    assert d1.equals(d2)
    d1 = iloc_pandas_on_spark(psdf, [1, 3]).to_pandas()
    d2 = pd.DataFrame({"x": [2, 3], "y": [1, 0]}, index=[0, 1])
    assert d1.equals(d2)
    assert iloc_pandas_on_spark(psds, 0) == 1
    assert iloc_pandas_on_spark(psds, slice(1, 3)).tolist() == [2, 2]
    assert iloc_pandas_on_spark(psds, [0, 3]).tolist() == [1, 3]


def test_spark_metric_loss_score():
    spark = SparkSession.builder.getOrCreate()
    scoreAndLabels = map(
        lambda x: (Vectors.dense([1.0 - x[0], x[0]]), x[1]),
        [
            (0.1, 0.0),
            (0.1, 1.0),
            (0.4, 0.0),
            (0.6, 0.0),
            (0.6, 1.0),
            (0.6, 1.0),
            (0.8, 1.0),
        ],
    )
    dataset = spark.createDataFrame(scoreAndLabels, ["raw", "label"])
    dataset = to_pandas_on_spark(dataset)
    # test pr_auc
    metric = spark_metric_loss_score(
        "pr_auc",
        dataset["raw"],
        dataset["label"],
    )
    print("pr_auc: ", metric)
    assert str(metric)[:5] == "0.166"
    # test roc_auc
    metric = spark_metric_loss_score(
        "roc_auc",
        dataset["raw"],
        dataset["label"],
    )
    print("roc_auc: ", metric)
    assert str(metric)[:5] == "0.291"

    scoreAndLabels = [
        (-28.98343821, -27.0),
        (20.21491975, 21.5),
        (-25.98418959, -22.0),
        (30.69731842, 33.0),
        (74.69283752, 71.0),
    ]
    dataset = spark.createDataFrame(scoreAndLabels, ["raw", "label"])
    dataset = to_pandas_on_spark(dataset)
    # test rmse
    metric = spark_metric_loss_score(
        "rmse",
        dataset["raw"],
        dataset["label"],
    )
    print("rmse: ", metric)
    assert str(metric)[:5] == "2.842"
    # test mae
    metric = spark_metric_loss_score(
        "mae",
        dataset["raw"],
        dataset["label"],
    )
    print("mae: ", metric)
    assert str(metric)[:5] == "2.649"
    # test r2
    metric = spark_metric_loss_score(
        "r2",
        dataset["raw"],
        dataset["label"],
    )
    print("r2: ", metric)
    assert str(metric)[:5] == "0.006"
    # test mse
    metric = spark_metric_loss_score(
        "mse",
        dataset["raw"],
        dataset["label"],
    )
    print("mse: ", metric)
    assert str(metric)[:5] == "8.079"
    # test var
    metric = spark_metric_loss_score(
        "var",
        dataset["raw"],
        dataset["label"],
    )
    print("var: ", metric)
    assert str(metric)[:5] == "-1489"

    predictionAndLabelsWithProbabilities = [
        (1.0, 1.0, 1.0, [0.1, 0.8, 0.1]),
        (0.0, 2.0, 1.0, [0.9, 0.05, 0.05]),
        (0.0, 0.0, 1.0, [0.8, 0.2, 0.0]),
        (1.0, 1.0, 1.0, [0.3, 0.65, 0.05]),
    ]
    dataset = spark.createDataFrame(
        predictionAndLabelsWithProbabilities,
        ["prediction", "label", "weight", "probability"],
    )
    dataset = to_pandas_on_spark(dataset)
    # test logloss
    metric = spark_metric_loss_score(
        "log_loss",
        dataset["probability"],
        dataset["label"],
    )
    print("log_loss: ", metric)
    assert str(metric)[:5] == "0.968"
    # test accuracy
    metric = spark_metric_loss_score(
        "accuracy",
        dataset["prediction"],
        dataset["label"],
    )
    print("accuracy: ", metric)
    assert str(metric)[:5] == "0.25"
    # test f1
    metric = spark_metric_loss_score(
        "f1",
        dataset["prediction"],
        dataset["label"],
    )
    print("f1: ", metric)
    assert str(metric)[:5] == "0.333"

    scoreAndLabels = [
        ([0.0, 1.0], [0.0, 2.0]),
        ([0.0, 2.0], [0.0, 1.0]),
        ([], [0.0]),
        ([2.0], [2.0]),
        ([2.0, 0.0], [2.0, 0.0]),
        ([0.0, 1.0, 2.0], [0.0, 1.0]),
        ([1.0], [1.0, 2.0]),
    ]
    dataset = spark.createDataFrame(scoreAndLabels, ["prediction", "label"])
    dataset = to_pandas_on_spark(dataset)
    # test micro_f1
    metric = spark_metric_loss_score(
        "micro_f1",
        dataset["prediction"],
        dataset["label"],
    )
    print("micro_f1: ", metric)
    assert str(metric)[:5] == "0.304"
    # test macro_f1
    metric = spark_metric_loss_score(
        "macro_f1",
        dataset["prediction"],
        dataset["label"],
    )
    print("macro_f1: ", metric)
    assert str(metric)[:5] == "0.111"

    scoreAndLabels = [
        (
            [1.0, 6.0, 2.0, 7.0, 8.0, 3.0, 9.0, 10.0, 4.0, 5.0],
            [1.0, 2.0, 3.0, 4.0, 5.0],
        ),
        ([4.0, 1.0, 5.0, 6.0, 2.0, 7.0, 3.0, 8.0, 9.0, 10.0], [1.0, 2.0, 3.0]),
        ([1.0, 2.0, 3.0, 4.0, 5.0], []),
    ]
    dataset = spark.createDataFrame(scoreAndLabels, ["prediction", "label"])
    dataset = to_pandas_on_spark(dataset)
    # test ap
    metric = spark_metric_loss_score(
        "ap",
        dataset["prediction"],
        dataset["label"],
    )
    print("ap: ", metric)
    assert str(metric)[:5] == "0.644"
    # test ndcg
    # ndcg is tested in synapseML rank tests, so we don't need to test it here


if __name__ == "__main__":
    # test_with_parameters_spark()
    # test_get_n_cpus_spark()
    # test_broadcast_code()
    # test_get_broadcast_data()
    # test_train_test_split_pyspark()
    # test_n_current_trials()
    # test_len_labels()
    # test_iloc_pandas_on_spark()
    test_spark_metric_loss_score()
