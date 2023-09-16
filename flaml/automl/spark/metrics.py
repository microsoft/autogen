import numpy as np
from typing import Union
from flaml.automl.spark import psSeries, F
from pyspark.ml.evaluation import (
    BinaryClassificationEvaluator,
    RegressionEvaluator,
    MulticlassClassificationEvaluator,
    MultilabelClassificationEvaluator,
    RankingEvaluator,
)


def ps_group_counts(groups: Union[psSeries, np.ndarray]) -> np.ndarray:
    if isinstance(groups, np.ndarray):
        _, i, c = np.unique(groups, return_counts=True, return_index=True)
    else:
        i = groups.drop_duplicates().index.values
        c = groups.value_counts().sort_index().to_numpy()
    return c[np.argsort(i)].tolist()


def _process_df(df, label_col, prediction_col):
    df = df.withColumn(label_col, F.array([df[label_col]]))
    df = df.withColumn(prediction_col, F.array([df[prediction_col]]))
    return df


def _compute_label_from_probability(df, probability_col, prediction_col):
    # array_max finds the maximum value in the 'probability' array
    # array_position finds the index of the maximum value in the 'probability' array
    max_index_expr = F.expr(f"array_position({probability_col}, array_max({probability_col}))-1")
    # Create a new column 'prediction' based on the maximum probability value
    df = df.withColumn(prediction_col, max_index_expr.cast("double"))
    return df


def spark_metric_loss_score(
    metric_name: str,
    y_predict: psSeries,
    y_true: psSeries,
    sample_weight: psSeries = None,
    groups: psSeries = None,
) -> float:
    """
    Compute the loss score of a metric for spark models.

    Args:
        metric_name: str | the name of the metric.
        y_predict: psSeries | the predicted values.
        y_true: psSeries | the true values.
        sample_weight: psSeries | the sample weights. Default: None.
        groups: psSeries | the group of each row. Default: None.

    Returns:
        float | the loss score. A lower value indicates a better model.
    """
    import warnings

    warnings.filterwarnings("ignore")

    label_col = "label"
    prediction_col = "prediction"
    kwargs = {}

    y_predict.name = prediction_col
    y_true.name = label_col
    df = y_predict.to_frame().join(y_true)
    if sample_weight is not None:
        sample_weight.name = "weight"
        df = df.join(sample_weight)
        kwargs = {"weightCol": "weight"}

    df = df.to_spark()

    metric_name = metric_name.lower()
    min_mode_metrics = ["log_loss", "rmse", "mse", "mae"]

    if metric_name == "rmse":
        evaluator = RegressionEvaluator(
            metricName="rmse",
            labelCol=label_col,
            predictionCol=prediction_col,
            **kwargs,
        )
    elif metric_name == "mse":
        evaluator = RegressionEvaluator(
            metricName="mse",
            labelCol=label_col,
            predictionCol=prediction_col,
            **kwargs,
        )
    elif metric_name == "mae":
        evaluator = RegressionEvaluator(
            metricName="mae",
            labelCol=label_col,
            predictionCol=prediction_col,
            **kwargs,
        )
    elif metric_name == "r2":
        evaluator = RegressionEvaluator(
            metricName="r2",
            labelCol=label_col,
            predictionCol=prediction_col,
            **kwargs,
        )
    elif metric_name == "var":
        evaluator = RegressionEvaluator(
            metricName="var",
            labelCol=label_col,
            predictionCol=prediction_col,
            **kwargs,
        )
    elif metric_name == "roc_auc":
        evaluator = BinaryClassificationEvaluator(
            metricName="areaUnderROC",
            labelCol=label_col,
            rawPredictionCol=prediction_col,
            **kwargs,
        )
    elif metric_name == "pr_auc":
        evaluator = BinaryClassificationEvaluator(
            metricName="areaUnderPR",
            labelCol=label_col,
            rawPredictionCol=prediction_col,
            **kwargs,
        )
    elif metric_name == "accuracy":
        evaluator = MulticlassClassificationEvaluator(
            metricName="accuracy",
            labelCol=label_col,
            predictionCol=prediction_col,
            **kwargs,
        )
    elif metric_name == "log_loss":
        # For log_loss, prediction_col should be probability, and we need to convert it to label
        df = _compute_label_from_probability(df, prediction_col, prediction_col + "_label")
        evaluator = MulticlassClassificationEvaluator(
            metricName="logLoss",
            labelCol=label_col,
            predictionCol=prediction_col + "_label",
            probabilityCol=prediction_col,
            **kwargs,
        )
    elif metric_name == "f1":
        evaluator = MulticlassClassificationEvaluator(
            metricName="f1",
            labelCol=label_col,
            predictionCol=prediction_col,
            **kwargs,
        )
    elif metric_name == "micro_f1":
        evaluator = MultilabelClassificationEvaluator(
            metricName="microF1Measure",
            labelCol=label_col,
            predictionCol=prediction_col,
            **kwargs,
        )
    elif metric_name == "macro_f1":
        evaluator = MultilabelClassificationEvaluator(
            metricName="f1MeasureByLabel",
            labelCol=label_col,
            predictionCol=prediction_col,
            **kwargs,
        )
    elif metric_name == "ap":
        evaluator = RankingEvaluator(
            metricName="meanAveragePrecision",
            labelCol=label_col,
            predictionCol=prediction_col,
        )
    elif "ndcg" in metric_name:
        # TODO: check if spark.ml ranker has the same format with
        # synapseML ranker, may need to adjust the format of df
        if "@" in metric_name:
            k = int(metric_name.split("@", 1)[-1])
            if groups is None:
                evaluator = RankingEvaluator(
                    metricName="ndcgAtK",
                    labelCol=label_col,
                    predictionCol=prediction_col,
                    k=k,
                )
                df = _process_df(df, label_col, prediction_col)
                score = 1 - evaluator.evaluate(df)
            else:
                counts = ps_group_counts(groups)
                score = 0
                psum = 0
                for c in counts:
                    y_true_ = y_true[psum : psum + c]
                    y_predict_ = y_predict[psum : psum + c]
                    df = y_true_.to_frame().join(y_predict_).to_spark()
                    df = _process_df(df, label_col, prediction_col)
                    evaluator = RankingEvaluator(
                        metricName="ndcgAtK",
                        labelCol=label_col,
                        predictionCol=prediction_col,
                        k=k,
                    )
                    score -= evaluator.evaluate(df)
                    psum += c
                score /= len(counts)
                score += 1
        else:
            evaluator = RankingEvaluator(metricName="ndcgAtK", labelCol=label_col, predictionCol=prediction_col)
            df = _process_df(df, label_col, prediction_col)
            score = 1 - evaluator.evaluate(df)
        return score
    else:
        raise ValueError(f"Unknown metric name: {metric_name} for spark models.")

    return evaluator.evaluate(df) if metric_name in min_mode_metrics else 1 - evaluator.evaluate(df)
