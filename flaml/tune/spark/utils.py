import logging
import os
import textwrap
import threading
import time
from functools import lru_cache, partial


logger = logging.getLogger(__name__)
logger_formatter = logging.Formatter(
    "[%(name)s: %(asctime)s] {%(lineno)d} %(levelname)s - %(message)s", "%m-%d %H:%M:%S"
)
logger.propagate = False
try:
    os.environ["PYARROW_IGNORE_TIMEZONE"] = "1"
    import pyspark
    from pyspark.sql import SparkSession
    from pyspark.util import VersionUtils
    import py4j

    _have_spark = True
    _spark_major_minor_version = VersionUtils.majorMinorVersion(pyspark.__version__)
except ImportError as e:
    logger.debug("Could not import pyspark: %s", e)
    _have_spark = False
    py4j = None
    _spark_major_minor_version = (0, 0)


@lru_cache(maxsize=2)
def check_spark():
    """Check if Spark is installed and running.
    Result of the function will be cached since test once is enough. As lru_cache will not
    cache exceptions, we don't raise exceptions here but only log a warning message.

    Returns:
        Return (True, None) if the check passes, otherwise log the exception message and
        return (False, Exception(msg)). The exception can be raised by the caller.
    """
    logger.debug("\ncheck Spark installation...This line should appear only once.\n")
    if not _have_spark:
        msg = """use_spark=True requires installation of PySpark. Please run pip install flaml[spark]
        and check [here](https://spark.apache.org/docs/latest/api/python/getting_started/install.html)
        for more details about installing Spark."""
        return False, ImportError(msg)

    if _spark_major_minor_version[0] < 3:
        msg = "Spark version must be >= 3.0 to use flaml[spark]"
        return False, ImportError(msg)

    try:
        SparkSession.builder.getOrCreate()
    except RuntimeError as e:
        # logger.warning(f"\nSparkSession is not available: {e}\n")
        return False, RuntimeError(e)

    return True, None


def get_n_cpus(node="driver"):
    """Get the number of CPU cores of the given type of node.

    Args:
        node: string | The type of node to get the number of cores. Can be 'driver' or 'executor'.
            Default is 'driver'.

    Returns:
        An int of the number of CPU cores.
    """
    assert node in ["driver", "executor"]
    try:
        n_cpus = int(SparkSession.builder.getOrCreate().sparkContext.getConf().get(f"spark.{node}.cores"))
    except (TypeError, RuntimeError):
        n_cpus = os.cpu_count()
    return n_cpus


def with_parameters(trainable, **kwargs):
    """Wrapper for trainables to pass arbitrary large data objects.

    This wrapper function will store all passed parameters in the Spark
    Broadcast variable.

    Args:
        trainable: Trainable to wrap.
        **kwargs: parameters to store in object store.

    Returns:
        A new function with partial application of the given arguments
        and keywords. The given arguments and keywords will be broadcasted
        to all the executors.


    ```python
    import pyspark
    import flaml
    from sklearn.datasets import load_iris
    def train(config, data=None):
        if isinstance(data, pyspark.broadcast.Broadcast):
            data = data.value
        print(config, data)

    data = load_iris()
    with_parameters_train = flaml.tune.spark.utils.with_parameters(train, data=data)
    with_parameters_train(config=1)
    train(config={"metric": "accuracy"})
    ```
    """

    if not callable(trainable):
        raise ValueError(
            f"`with_parameters() only works with function trainables`. " f"Got type: " f"{type(trainable)}."
        )

    spark_available, spark_error_msg = check_spark()
    if not spark_available:
        raise spark_error_msg
    spark = SparkSession.builder.getOrCreate()

    bc_kwargs = dict()
    for k, v in kwargs.items():
        bc_kwargs[k] = spark.sparkContext.broadcast(v)

    return partial(trainable, **bc_kwargs)


def broadcast_code(custom_code="", file_name="mylearner"):
    """Write customized learner/metric code contents to a file for importing.
    It is necessary for using the customized learner/metric in spark backend.
    The path of the learner/metric file will be returned.

    Args:
        custom_code: str, default="" | code contents of the custom learner/metric.
        file_name: str, default="mylearner" | file name of the custom learner/metric.

    Returns:
        The path of the custom code file.
    ```python
    from flaml.tune.spark.utils import broadcast_code
    from flaml.automl.model import LGBMEstimator

    custom_code = '''
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
    '''

    broadcast_code(custom_code=custom_code)
    from flaml.tune.spark.mylearner import MyLargeLGBM
    assert isinstance(MyLargeLGBM(), LGBMEstimator)
    ```
    """
    flaml_path = os.path.dirname(os.path.abspath(__file__))
    custom_code = textwrap.dedent(custom_code)
    custom_path = os.path.join(flaml_path, file_name + ".py")

    with open(custom_path, "w") as f:
        f.write(custom_code)

    return custom_path


def get_broadcast_data(broadcast_data):
    """Get the broadcast data from the broadcast variable.

    Args:
        broadcast_data: pyspark.broadcast.Broadcast | the broadcast variable.

    Returns:
        The broadcast data.
    """
    if _have_spark and isinstance(broadcast_data, pyspark.broadcast.Broadcast):
        broadcast_data = broadcast_data.value
    return broadcast_data


class PySparkOvertimeMonitor:
    """A context manager class to monitor if the PySpark job is overtime.
    Example:

    ```python
    with PySparkOvertimeMonitor(time_start, time_budget_s, force_cancel, parallel=parallel):
        results = parallel(
            delayed(evaluation_function)(trial_to_run.config)
            for trial_to_run in trials_to_run
        )
    ```

    """

    def __init__(
        self,
        start_time,
        time_budget_s,
        force_cancel=False,
        cancel_func=None,
        parallel=None,
        sc=None,
    ):
        """Constructor.

        Specify the time budget and start time of the PySpark job, and specify how to cancel them.

        Args:
            Args relate to monitoring:
                start_time: float | The start time of the PySpark job.
                time_budget_s: float | The time budget of the PySpark job in seconds.
                force_cancel: boolean, default=False | Whether to forcely cancel the PySpark job if overtime.

            Args relate to how to cancel the PySpark job:
            (Only one of the following args will work. Priorities from top to bottom)
                cancel_func: function | A function to cancel the PySpark job.
                parallel: joblib.parallel.Parallel | Specify this if using joblib_spark as a parallel backend. It will call parallel._backend.terminate() to cancel the jobs.
                sc: pyspark.SparkContext object | You can pass a specific SparkContext.

                If all three args is None, the monitor will call pyspark.SparkContext.getOrCreate().cancelAllJobs() to cancel the jobs.


        """
        self._time_budget_s = time_budget_s
        self._start_time = start_time
        self._force_cancel = force_cancel
        # TODO: add support for non-spark scenario
        if self._force_cancel and _have_spark:
            self._monitor_daemon = None
            self._finished_flag = False
            self._cancel_flag = False
            self.sc = None
            if cancel_func:
                self.__cancel_func = cancel_func
            elif parallel:
                self.__cancel_func = parallel._backend.terminate
            elif sc:
                self.sc = sc
                self.__cancel_func = self.sc.cancelAllJobs
            else:
                self.__cancel_func = pyspark.SparkContext.getOrCreate().cancelAllJobs
            # logger.info(self.__cancel_func)

    def _monitor_overtime(self):
        """The lifecycle function for monitor thread."""
        if self._time_budget_s is None:
            self.__cancel_func()
            self._cancel_flag = True
            return
        while time.time() - self._start_time <= self._time_budget_s:
            time.sleep(0.01)
            if self._finished_flag:
                return
        self.__cancel_func()
        self._cancel_flag = True
        return

    def _setLogLevel(self, level):
        """Set the log level of the spark context.
        Set the level to OFF could block the warning message of Spark."""
        if self.sc:
            self.sc.setLogLevel(level)
        else:
            pyspark.SparkContext.getOrCreate().setLogLevel(level)

    def __enter__(self):
        """Enter the context manager.
        This will start a monitor thread if spark is available and force_cancel is True.
        """
        if self._force_cancel and _have_spark:
            self._monitor_daemon = threading.Thread(target=self._monitor_overtime)
            # logger.setLevel("INFO")
            logger.info("monitor started")
            self._setLogLevel("OFF")
            self._monitor_daemon.start()

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """Exit the context manager.
        This will wait for the monitor thread to nicely exit."""
        if self._force_cancel and _have_spark:
            self._finished_flag = True
            self._monitor_daemon.join()
            if self._cancel_flag:
                print()
                logger.warning("Time exceeded, canceled jobs")
            # self._setLogLevel("WARN")
            if not exc_type:
                return True
            elif exc_type == py4j.protocol.Py4JJavaError:
                return True
            else:
                return False
