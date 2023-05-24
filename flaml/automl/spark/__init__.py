import os

os.environ["PYARROW_IGNORE_TIMEZONE"] = "1"
try:
    import pyspark
    import pyspark.pandas as ps
    import pyspark.sql.functions as F
    import pyspark.sql.types as T
    from pyspark.sql import DataFrame as sparkDataFrame
    from pyspark.pandas import DataFrame as psDataFrame, Series as psSeries, set_option
    from pyspark.util import VersionUtils
except ImportError:

    class psDataFrame:
        pass

    F = T = ps = sparkDataFrame = psSeries = psDataFrame
    _spark_major_minor_version = set_option = None
    ERROR = ImportError(
        """Please run pip install flaml[spark]
    and check [here](https://spark.apache.org/docs/latest/api/python/getting_started/install.html)
    for more details about installing Spark."""
    )
else:
    ERROR = None
    _spark_major_minor_version = VersionUtils.majorMinorVersion(pyspark.__version__)

try:
    import pandas as pd
    from pandas import DataFrame, Series
except ImportError:
    DataFrame = Series = pd = None
