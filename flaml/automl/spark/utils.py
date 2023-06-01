import logging
from typing import Union, List, Optional, Tuple
import numpy as np
from flaml.automl.spark import (
    sparkDataFrame,
    ps,
    F,
    T,
    psDataFrame,
    psSeries,
    _spark_major_minor_version,
    DataFrame,
    Series,
    set_option,
)

logger = logging.getLogger(__name__)
logger_formatter = logging.Formatter(
    "[%(name)s: %(asctime)s] {%(lineno)d} %(levelname)s - %(message)s", "%m-%d %H:%M:%S"
)
logger.propagate = False


def to_pandas_on_spark(
    df: Union[DataFrame, sparkDataFrame, Series, psDataFrame, psSeries],
    index_col: Optional[str] = None,
    default_index_type: Optional[str] = "distributed-sequence",
) -> Union[psDataFrame, psSeries]:
    """Convert pandas or pyspark dataframe/series to pandas_on_Spark dataframe/series.

    Args:
        df: pandas.DataFrame/series or pyspark dataframe | The input dataframe/series.
        index_col: str, optional | The column name to use as index, default None.
        default_index_type: str, optional | The default index type, default "distributed-sequence".

    Returns:
        pyspark.pandas.DataFrame/Series: The converted pandas-on-Spark dataframe/series.

    ```python
    import pandas as pd
    from flaml.automl.spark.utils import to_pandas_on_spark

    pdf = DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
    psdf = to_pandas_on_spark(pdf)
    print(psdf)

    from pyspark.sql import SparkSession

    spark = SparkSession.builder.getOrCreate()
    sdf = spark.createDataFrame(pdf)
    psdf = to_pandas_on_spark(sdf)
    print(psdf)

    pds = Series([1, 2, 3])
    pss = to_pandas_on_spark(pds)
    print(pss)
    ```
    """
    set_option("compute.default_index_type", default_index_type)
    if isinstance(df, (DataFrame, Series)):
        return ps.from_pandas(df)
    elif isinstance(df, sparkDataFrame):
        if _spark_major_minor_version[0] == 3 and _spark_major_minor_version[1] < 3:
            return df.to_pandas_on_spark(index_col=index_col)
        else:
            return df.pandas_api(index_col=index_col)
    elif isinstance(df, (psDataFrame, psSeries)):
        return df
    else:
        raise TypeError(f"{type(df)} is not one of pandas.DataFrame, pandas.Series and pyspark.sql.DataFrame")


def train_test_split_pyspark(
    df: Union[sparkDataFrame, psDataFrame],
    stratify_column: Optional[str] = None,
    test_fraction: Optional[float] = 0.2,
    seed: Optional[int] = 1234,
    to_pandas_spark: Optional[bool] = True,
    index_col: Optional[str] = "tmp_index_col",
) -> Tuple[Union[sparkDataFrame, psDataFrame], Union[sparkDataFrame, psDataFrame]]:
    """Split a pyspark dataframe into train and test dataframes.

    Args:
        df: pyspark.sql.DataFrame | The input dataframe.
        stratify_column: str | The column name to stratify the split. Default None.
        test_fraction: float | The fraction of the test data. Default 0.2.
        seed: int | The random seed. Default 1234.
        to_pandas_spark: bool | Whether to convert the output to pandas_on_spark. Default True.
        index_col: str | The column name to use as index. Default None.

    Returns:
        pyspark.sql.DataFrame/pandas_on_spark DataFrame | The train dataframe.
        pyspark.sql.DataFrame/pandas_on_spark DataFrame | The test dataframe.
    """
    import warnings

    warnings.filterwarnings("ignore")

    if isinstance(df, psDataFrame):
        df = df.to_spark(index_col=index_col)

    if stratify_column:
        # Test data
        test_fraction_dict = (
            df.select(stratify_column).distinct().withColumn("fraction", F.lit(test_fraction)).rdd.collectAsMap()
        )
        df_test = df.stat.sampleBy(stratify_column, test_fraction_dict, seed)
        # Train data
        df_train = df.subtract(df_test)
    else:
        df_train, df_test = df.randomSplit([1 - test_fraction, test_fraction], seed)

    if to_pandas_spark:
        df_train = to_pandas_on_spark(df_train, index_col=index_col)
        df_test = to_pandas_on_spark(df_test, index_col=index_col)
        df_train.index.name = None
        df_test.index.name = None
    elif index_col == "tmp_index_col":
        df_train = df_train.drop(index_col)
        df_test = df_test.drop(index_col)
    return [df_train, df_test]


def unique_pandas_on_spark(psds: Union[psSeries, psDataFrame]) -> Tuple[np.ndarray, np.ndarray]:
    """Get the unique values and counts of a pandas_on_spark series."""
    if isinstance(psds, psDataFrame):
        psds = psds.iloc[:, 0]
    _tmp = psds.value_counts().to_pandas()
    label_set = _tmp.index.values
    counts = _tmp.values
    return label_set, counts


def len_labels(y: Union[psSeries, np.ndarray], return_labels=False) -> Union[int, Optional[np.ndarray]]:
    """Get the number of unique labels in y."""
    if not isinstance(y, (psDataFrame, psSeries)):
        labels = np.unique(y)
    else:
        labels = y.unique() if isinstance(y, psSeries) else y.iloc[:, 0].unique()
    if return_labels:
        return len(labels), labels
    return len(labels)


def unique_value_first_index(y: Union[Series, psSeries, np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
    """Get the unique values and indices of a pandas series,
    pandas_on_spark series or numpy array."""
    if isinstance(y, psSeries):
        y_unique = y.drop_duplicates().sort_index()
        label_set = y_unique.values
        first_index = y_unique.index.values
    else:
        label_set, first_index = np.unique(y, return_index=True)
    return label_set, first_index


def iloc_pandas_on_spark(
    psdf: Union[psDataFrame, psSeries, DataFrame, Series],
    index: Union[int, slice, list],
    index_col: Optional[str] = "tmp_index_col",
) -> Union[psDataFrame, psSeries]:
    """Get the rows of a pandas_on_spark dataframe/series by index."""
    import warnings

    warnings.filterwarnings("ignore")

    if isinstance(psdf, (DataFrame, Series)):
        return psdf.iloc[index]
    if isinstance(index, (int, slice)):
        if isinstance(psdf, psSeries):
            return psdf.iloc[index]
        else:
            return psdf.iloc[index, :]
    elif isinstance(index, list):
        if isinstance(psdf, psSeries):
            sdf = psdf.to_frame().to_spark(index_col=index_col)
        else:
            if index_col not in psdf.columns:
                sdf = psdf.to_spark(index_col=index_col)
            else:
                sdf = psdf.to_spark()
        sdfiloc = sdf.filter(F.col(index_col).isin(index))
        psdfiloc = to_pandas_on_spark(sdfiloc)
        if isinstance(psdf, psSeries):
            psdfiloc = psdfiloc[psdfiloc.columns.drop(index_col)[0]]
        elif index_col not in psdf.columns:
            psdfiloc = psdfiloc.drop(columns=[index_col])
        return psdfiloc
    else:
        raise TypeError(f"{type(index)} is not one of int, slice and list for pandas_on_spark iloc")


def spark_kFold(
    dataset: Union[sparkDataFrame, psDataFrame],
    nFolds: int = 3,
    foldCol: str = "",
    seed: int = 42,
    index_col: Optional[str] = "tmp_index_col",
) -> List[Tuple[psDataFrame, psDataFrame]]:
    """Generate k-fold splits for a Spark DataFrame.
    Adopted from https://spark.apache.org/docs/latest/api/python/_modules/pyspark/ml/tuning.html#CrossValidator

    Args:
        dataset: sparkDataFrame / psDataFrame. | The DataFrame to split.
        nFolds: int | The number of folds. Default is 3.
        foldCol: str | The column name to use for fold numbers. If not specified,
            the DataFrame will be randomly split. Default is "".
            The same group will not appear in two different folds (the number of
            distinct groups has to be at least equal to the number of folds).
            The folds are approximately balanced in the sense that the number of
            distinct groups is approximately the same in each fold.
        seed: int | The random seed. Default is 42.
        index_col: str | The name of the index column. Default is "tmp_index_col".

    Returns:
        A list of (train, validation) DataFrames.
    """
    import warnings

    warnings.filterwarnings("ignore")

    if isinstance(dataset, psDataFrame):
        dataset = dataset.to_spark(index_col=index_col)

    datasets = []
    if not foldCol:
        # Do random k-fold split.
        h = 1.0 / nFolds
        randCol = f"rand_col_{seed}"
        df = dataset.select("*", F.rand(seed).alias(randCol))
        for i in range(nFolds):
            validateLB = i * h
            validateUB = (i + 1) * h
            condition = (df[randCol] >= validateLB) & (df[randCol] < validateUB)
            validation = to_pandas_on_spark(df.filter(condition), index_col=index_col)
            train = to_pandas_on_spark(df.filter(~condition), index_col=index_col)
            datasets.append((train.drop(columns=[randCol]), validation.drop(columns=[randCol])))
    else:
        # Use user-specified fold column
        def get_fold_num(foldNum: int) -> int:
            return int(foldNum % nFolds)

        get_fold_num_udf = F.UserDefinedFunction(get_fold_num, T.IntegerType())
        for i in range(nFolds):
            training = dataset.filter(get_fold_num_udf(dataset[foldCol]) != F.lit(i))
            validation = dataset.filter(get_fold_num_udf(dataset[foldCol]) == F.lit(i))
            if training.rdd.getNumPartitions() == 0 or len(training.take(1)) == 0:
                raise ValueError("The training data at fold %s is empty." % i)
            if validation.rdd.getNumPartitions() == 0 or len(validation.take(1)) == 0:
                raise ValueError("The validation data at fold %s is empty." % i)
            training = to_pandas_on_spark(training, index_col=index_col)
            validation = to_pandas_on_spark(validation, index_col=index_col)
            datasets.append((training, validation))

    return datasets
