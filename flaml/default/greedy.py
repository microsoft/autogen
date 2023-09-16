import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import pairwise_distances


def _augment(row):
    max, avg, id = row.max(), row.mean(), row.index[0]
    return row.apply(lambda x: (x, max, avg, id))


def construct_portfolio(regret_matrix, meta_features, regret_bound):
    """The portfolio construction algorithm.

    (Reference)[https://arxiv.org/abs/2202.09927].

    Args:
        regret_matrix: A dataframe of regret matrix.
        meta_features: None or a dataframe of metafeatures matrix.
            When set to None, the algorithm uses greedy strategy.
            Otherwise, the algorithm uses greedy strategy with feedback
            from the nearest neighbor predictor.
        regret_bound: A float of the regret bound.

    Returns:
        A list of configuration names.
    """
    configs = []
    all_configs = set(regret_matrix.index.tolist())
    tasks = regret_matrix.columns
    # pre-processing
    if meta_features is not None:
        scaler = RobustScaler()
        meta_features = meta_features.loc[tasks]
        meta_features.loc[:, :] = scaler.fit_transform(meta_features)
        nearest_task = {}
        for t in tasks:
            other_meta_features = meta_features.drop(t)
            dist = pd.DataFrame(
                pairwise_distances(
                    meta_features.loc[t].to_numpy().reshape(1, -1),
                    other_meta_features,
                    metric="l2",
                ),
                columns=other_meta_features.index,
            )
            nearest_task[t] = dist.idxmin(axis=1)
        regret_matrix = regret_matrix.apply(_augment, axis=1)
        print(regret_matrix)

    def loss(configs):
        """Loss of config set `configs`, according to nearest neighbor config predictor."""
        if meta_features is not None:
            r = []
            best_config_per_task = regret_matrix.loc[configs, :].min()
            for t in tasks:
                config = best_config_per_task[nearest_task[t]].iloc[0][-1]
                r.append(regret_matrix[t][config][0])
        else:
            r = regret_matrix.loc[configs].min()
        excessive_regret = (np.array(r) - regret_bound).clip(min=0).sum()
        avg_regret = np.array(r).mean()
        return excessive_regret, avg_regret

    prev = np.inf
    i = 0
    eps = 1e-5
    while True:
        candidates = [configs + [d] for d in all_configs.difference(configs)]
        losses, avg_regret = tuple(zip(*(loss(x) for x in candidates)))
        sorted_losses = np.sort(losses)
        if sorted_losses[1] - sorted_losses[0] < eps:
            minloss = np.nanmin(losses)
            print(f"tie detected at loss = {sorted_losses[0]}, using alternative metric.")
            tied = np.flatnonzero(losses - minloss < eps)
            losses = [(avg_regret[i], i) for i in tied]
            minloss, ind = min(losses)
            if minloss > prev - eps:
                print(f"May be overfitting at k = {i + 1}, current = {minloss:.5f}, " f"prev = {prev:.5f}. Stopping.")
                break
            configs = candidates[ind]
            prev = minloss
        else:
            configs = candidates[np.nanargmin(losses)]
        i += 1
        if sorted_losses[0] <= eps:
            print(f"Reached target regret bound of {regret_bound}! k = {i}. Declining to pick further!")
            break

    return configs
