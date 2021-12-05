"""Require: pip install flaml[test,ray]
"""
from logging import raiseExceptions
from flaml.scheduler.trial_scheduler import TrialScheduler
import numpy as np
from flaml import tune
import time


def rand_vector_unit_sphere(dim):
    """this function allows you to generate
    points that uniformly distribute on
    the (dim-1)-sphere.
    """
    vec = np.random.normal(0, 1, dim)
    mag = np.linalg.norm(vec)
    return vec / mag


def simple_obj(config, resource=10000):
    config_value_vector = np.array([config["x"], config["y"], config["z"]])
    score_sequence = []
    for i in range(resource):
        a = rand_vector_unit_sphere(3)
        a[2] = abs(a[2])
        point_projection = np.dot(config_value_vector, a)
        score_sequence.append(point_projection)
    score_avg = np.mean(np.array(score_sequence))
    score_std = np.std(np.array(score_sequence))
    score_lb = score_avg - 1.96 * score_std / np.sqrt(resource)
    tune.report(samplesize=resource, sphere_projection=score_lb)


def obj_w_intermediate_report(resource, config):
    config_value_vector = np.array([config["x"], config["y"], config["z"]])
    score_sequence = []
    for i in range(resource):
        a = rand_vector_unit_sphere(3)
        a[2] = abs(a[2])
        point_projection = np.dot(config_value_vector, a)
        score_sequence.append(point_projection)
        if (i + 1) % 100 == 0:
            score_avg = np.mean(np.array(score_sequence))
            score_std = np.std(np.array(score_sequence))
            score_lb = score_avg - 1.96 * score_std / np.sqrt(i + 1)
            tune.report(samplesize=i + 1, sphere_projection=score_lb)


def obj_w_suggested_resource(resource_attr, config):
    resource = config[resource_attr]
    simple_obj(config, resource)


def test_scheduler(scheduler=None):
    from functools import partial

    resource_attr = "samplesize"
    max_resource = 10000

    # specify the objective functions
    if scheduler is None:
        evaluation_obj = simple_obj
    elif scheduler == "flaml":
        evaluation_obj = partial(obj_w_suggested_resource, resource_attr)
    elif scheduler == "asha" or isinstance(scheduler, TrialScheduler):
        evaluation_obj = partial(obj_w_intermediate_report, max_resource)
    else:
        try:
            from ray.tune.schedulers import TrialScheduler as RayTuneTrialScheduler
        except ImportError:
            print(
                "skip this condition, which may require TrialScheduler from ray tune, \
                as ray tune cannot be imported."
            )
            return
        if isinstance(scheduler, RayTuneTrialScheduler):
            evaluation_obj = partial(obj_w_intermediate_report, max_resource)
        else:
            raise ValueError

    analysis = tune.run(
        evaluation_obj,
        config={
            "x": tune.uniform(5, 20),
            "y": tune.uniform(0, 10),
            "z": tune.uniform(0, 10),
        },
        metric="sphere_projection",
        mode="max",
        verbose=1,
        resource_attr=resource_attr,
        scheduler=scheduler,
        max_resource=max_resource,
        min_resource=100,
        reduction_factor=2,
        time_budget_s=1,
        num_samples=500,
    )

    print("Best hyperparameters found were: ", analysis.best_config)
    # print(analysis.get_best_trial)
    return analysis.best_config


def test_no_scheduler():
    best_config = test_scheduler()
    print("No scheduler, test error:", abs(10 / 2 - best_config["z"] / 2))


def test_asha_scheduler():
    try:
        from ray.tune.schedulers import ASHAScheduler
    except ImportError:
        print("skip the test as ray tune cannot be imported.")
        return
    best_config = test_scheduler(scheduler="asha")
    print("Auto ASHA scheduler, test error:", abs(10 / 2 - best_config["z"] / 2))


def test_custom_scheduler():
    try:
        from ray.tune.schedulers import HyperBandScheduler
    except ImportError:
        print("skip the test as ray tune cannot be imported.")
        return
    my_scheduler = HyperBandScheduler(
        time_attr="samplesize", max_t=1000, reduction_factor=2
    )
    best_config = test_scheduler(scheduler=my_scheduler)
    print("Custom ASHA scheduler, test error:", abs(10 / 2 - best_config["z"] / 2))


def test_custom_scheduler_default_time_attr():
    try:
        from ray.tune.schedulers import ASHAScheduler
    except ImportError:
        print("skip the test as ray tune cannot be imported.")
        return
    my_scheduler = ASHAScheduler(max_t=10)
    best_config = test_scheduler(scheduler=my_scheduler)
    print(
        "Custom ASHA scheduler (with ASHA default time attr), test error:",
        abs(10 / 2 - best_config["z"] / 2),
    )


def test_flaml_scheduler():
    best_config = test_scheduler(scheduler="flaml")
    print("FLAML scheduler, test error", abs(10 / 2 - best_config["z"] / 2))


if __name__ == "__main__":
    test_no_scheduler()
    test_asha_scheduler()
    test_custom_scheduler()
    test_custom_scheduler_default_time_attr()
    test_flaml_scheduler()
