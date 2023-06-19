import math
import datetime
from functools import lru_cache

import pandas as pd


def monthly_fourier_features(timestamps: pd.Series, month_fourier_degree: int = 2):
    if len(timestamps):
        data = pd.DataFrame({"time": timestamps})
        month_pos = timestamps.apply(lambda x: position_in_month(datetime.date(x.year, x.month, x.day)))
        for d in range(month_fourier_degree):
            data[f"cos{d+1}"] = (2 * (d + 1) * math.pi * month_pos).apply(math.cos)
            data[f"sin{d + 1}"] = (2 * (d + 1) * math.pi * month_pos).apply(math.sin)

        drop_cols = ["time"]
        data = data.drop(columns=drop_cols)
        return data
    else:
        columns = []
        for d in range(month_fourier_degree):
            columns += [f"cos{d+1}", f"sin{d + 1}"]

        return pd.DataFrame(columns=columns)


@lru_cache(maxsize=4096)
def position_in_month(d: datetime.date):
    prev = datetime.date(d.year, d.month, 1) - datetime.timedelta(days=1)
    nxt = datetime.date(
        d.year + 1 if d.month == 12 else d.year, 1 if d.month == 12 else d.month + 1, 1
    ) - datetime.timedelta(days=1)
    delta = (d - prev).days / (nxt - prev).days
    return delta
