"""Reward processors

Each method takes the metadata with the following keys:
    - env_reward: MiniWoB official reward
    - raw_reward: Raw task reward without time penalty
    - done: Whether the task is done
Then it returns a reward (float).
"""


def get_original_reward(metadata):
    return float(metadata["env_reward"])


def get_raw_reward(metadata):
    """Get the raw reward without time penalty.
    This is usually 1 for success and -1 for failure, but not always.
    """
    return float(metadata["raw_reward"])


def get_click_checkboxes_hard(metadata):
    """(click-checkboxes task) Reward without partial credits.
    Give 1 if the raw reward is 1. Otherwise, give -1.
    """
    if not metadata["done"]:
        return 0.0
    return 1.0 if metadata["raw_reward"] == 1.0 else -1.0


def raw_reward_threshold(threshold):
    """Return a reward processor that cut off at a threshold."""

    def fn(metadata):
        if metadata["raw_reward"] > threshold:
            return 1.0
        elif metadata["raw_reward"] > 0:
            return -1
        return metadata["raw_reward"]

    return fn


def get_reward_processor(config):
    if config.type == "time_independent":
        return get_raw_reward
    elif config.type == "time_discounted":
        return get_original_reward
    elif config.type == "click_checkboxes_hard":
        return get_click_checkboxes_hard
    else:
        raise ValueError("{} not a valid reward processor type".format(config.type))
