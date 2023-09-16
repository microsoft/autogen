import numpy as np
import logging
import time
import math
import copy
import collections
from typing import Optional, Union
from flaml.tune import Trial

try:
    from sklearn.metrics import mean_squared_error, mean_absolute_error
except ImportError:
    pass

logger = logging.getLogger(__name__)


def get_ns_feature_dim_from_vw_example(vw_example) -> dict:
    """Get a dictionary of feature dimensionality for each namespace singleton."""
    # *************************A NOTE about the input vwexample***********
    # Assumption: assume the vw_example takes one of the following format
    # depending on whether the example includes the feature names.

    # format 1: `y |ns1 feature1:feature_value1 feature2:feature_value2 |ns2
    #         ns2 feature3:feature_value3 feature4:feature_value4`
    # format 2: `y | ns1 feature_value1 feature_value2 |
    #         ns2 feature_value3 feature_value4`

    # The output of both cases are `{'ns1': 2, 'ns2': 2}`.

    # For more information about the input formate of vw example, please refer to
    # https://github.com/VowpalWabbit/vowpal_wabbit/wiki/Input-format.

    ns_feature_dim = {}
    data = vw_example.split("|")
    for i in range(1, len(data)):
        if ":" in data[i]:
            ns_w_feature = data[i].split(" ")
            ns = ns_w_feature[0]
            feature = ns_w_feature[1:]
            feature_dim = len(feature)
        else:
            data_split = data[i].split(" ")
            ns = data_split[0]
            feature_dim = len(data_split) - 1
            if len(data_split[-1]) == 0:
                feature_dim -= 1
        ns_feature_dim[ns] = feature_dim
    logger.debug("name space feature dimension %s", ns_feature_dim)
    return ns_feature_dim


class OnlineResult:
    """Class for managing the result statistics of a trial."""

    prob_delta = 0.1
    LOSS_MIN = 0.0
    LOSS_MAX = np.inf
    CB_COEF = 0.05  # 0.001 for mse

    def __init__(
        self,
        result_type_name: str,
        cb_coef: Optional[float] = None,
        init_loss: Optional[float] = 0.0,
        init_cb: Optional[float] = 100.0,
        mode: Optional[str] = "min",
        sliding_window_size: Optional[int] = 100,
    ):
        """Constructor.

        Args:
            result_type_name: A String to specify the name of the result type.
            cb_coef: a string to specify the coefficient on the confidence bound.
            init_loss: a float to specify the inital loss.
            init_cb: a float to specify the intial confidence bound.
            mode: A string in ['min', 'max'] to specify the objective as
                minimization or maximization.
            sliding_window_size: An int to specify the size of the sliding window
                (for experimental purpose).
        """
        self._result_type_name = result_type_name  # for example 'mse' or 'mae'
        self._mode = mode
        self._init_loss = init_loss
        # statistics needed for alg
        self.observation_count = 0
        self.resource_used = 0.0
        self._loss_avg = 0.0
        self._loss_cb = init_cb  # a large number (TODO: this can be changed)
        self._cb_coef = cb_coef if cb_coef is not None else self.CB_COEF
        # optional statistics
        self._sliding_window_size = sliding_window_size
        self._loss_queue = collections.deque(maxlen=self._sliding_window_size)

    def update_result(
        self,
        new_loss,
        new_resource_used,
        data_dimension,
        bound_of_range=1.0,
        new_observation_count=1.0,
    ):
        """Update result statistics."""
        self.resource_used += new_resource_used
        # keep the running average instead of sum of loss to avoid over overflow
        self._loss_avg = self._loss_avg * (
            self.observation_count / (self.observation_count + new_observation_count)
        ) + new_loss / (self.observation_count + new_observation_count)
        self.observation_count += new_observation_count
        self._loss_cb = self._update_loss_cb(bound_of_range, data_dimension)
        self._loss_queue.append(new_loss)

    def _update_loss_cb(self, bound_of_range, data_dim, bound_name="sample_complexity_bound"):
        """Calculate the coefficient of the confidence bound."""
        if bound_name == "sample_complexity_bound":
            # set the coefficient in the loss bound
            if "mae" in self.result_type_name:
                coef = self._cb_coef * bound_of_range
            else:
                coef = 0.001 * bound_of_range

            comp_F = math.sqrt(data_dim)
            n = self.observation_count
            return coef * comp_F * math.sqrt((np.log10(n / OnlineResult.prob_delta)) / n)
        else:
            raise NotImplementedError

    @property
    def result_type_name(self):
        return self._result_type_name

    @property
    def loss_avg(self):
        return self._loss_avg if self.observation_count != 0 else self._init_loss

    @property
    def loss_cb(self):
        return self._loss_cb

    @property
    def loss_lcb(self):
        return max(self._loss_avg - self._loss_cb, OnlineResult.LOSS_MIN)

    @property
    def loss_ucb(self):
        return min(self._loss_avg + self._loss_cb, OnlineResult.LOSS_MAX)

    @property
    def loss_avg_recent(self):
        return sum(self._loss_queue) / len(self._loss_queue) if len(self._loss_queue) != 0 else self._init_loss

    def get_score(self, score_name, cb_ratio=1):
        if "lcb" in score_name:
            return max(self._loss_avg - cb_ratio * self._loss_cb, OnlineResult.LOSS_MIN)
        elif "ucb" in score_name:
            return min(self._loss_avg + cb_ratio * self._loss_cb, OnlineResult.LOSS_MAX)
        elif "avg" in score_name:
            return self._loss_avg
        else:
            raise NotImplementedError


class BaseOnlineTrial(Trial):
    """Class for the online trial."""

    def __init__(
        self,
        config: dict,
        min_resource_lease: float,
        is_champion: Optional[bool] = False,
        is_checked_under_current_champion: Optional[bool] = True,
        custom_trial_name: Optional[str] = "mae",
        trial_id: Optional[str] = None,
    ):
        """Constructor.

        Args:
            config: The configuration dictionary.
            min_resource_lease: A float specifying the minimum resource lease.
            is_champion: A bool variable indicating whether the trial is champion.
            is_checked_under_current_champion: A bool indicating whether the trial
                has been used under the current champion.
            custom_trial_name: A string of a custom trial name.
            trial_id: A string for the trial id.
        """
        # ****basic variables
        self.config = config
        self.trial_id = trial_id
        self.status = Trial.PENDING
        self.start_time = time.time()
        self.custom_trial_name = custom_trial_name

        # ***resource budget related variable
        self._min_resource_lease = min_resource_lease
        self._resource_lease = copy.copy(self._min_resource_lease)
        # ***champion related variables
        self._is_champion = is_champion
        # self._is_checked_under_current_champion_ is supposed to be always 1 when the trial is first created
        self._is_checked_under_current_champion = is_checked_under_current_champion

    @property
    def is_champion(self):
        return self._is_champion

    @property
    def is_checked_under_current_champion(self):
        return self._is_checked_under_current_champion

    @property
    def resource_lease(self):
        return self._resource_lease

    def set_checked_under_current_champion(self, checked_under_current_champion: bool):
        # This is needed because sometimes
        # we want to know whether a trial has been paused since a new champion is promoted.
        # We want to try to pause those running trials (even though they are not yet achieve
        # the next scheduling check point according to resource used and resource lease),
        # because a better trial is likely to be in the new challengers generated by the new
        # champion, so we want to try them as soon as possible.
        # If we wait until we reach the next scheduling point, we may waste a lot of resource
        # (depending on what is the current resource lease) on the old trials (note that new
        # trials is not possible to be scheduled to run until there is a slot openning).
        # Intuitively speaking, we want to squize an opening slot as soon as possible once
        # a new champion is promoted, such that we are able to try newly generated challengers.
        self._is_checked_under_current_champion = checked_under_current_champion

    def set_resource_lease(self, resource: float):
        """Sets the resource lease accordingly."""
        self._resource_lease = resource

    def set_status(self, status):
        """Sets the status of the trial and record the start time."""
        self.status = status
        if status == Trial.RUNNING:
            if self.start_time is None:
                self.start_time = time.time()


class VowpalWabbitTrial(BaseOnlineTrial):
    """The class for Vowpal Wabbit online trials."""

    # NOTE: 1. About namespaces in vw:
    # - Wiki in vw:
    # https://github.com/VowpalWabbit/vowpal_wabbit/wiki/Namespaces
    # - Namespace vs features:
    # https://stackoverflow.com/questions/28586225/in-vowpal-wabbit-what-is-the-difference-between-a-namespace-and-feature

    # About result:
    # 1. training related results (need to be updated in the trainable class)
    # 2. result about resources lease (need to be updated externally)
    cost_unit = 1.0
    interactions_config_key = "interactions"
    MIN_RES_CONST = 5

    def __init__(
        self,
        config: dict,
        min_resource_lease: float,
        metric: str = "mae",
        is_champion: Optional[bool] = False,
        is_checked_under_current_champion: Optional[bool] = True,
        custom_trial_name: Optional[str] = "vw_mae_clipped",
        trial_id: Optional[str] = None,
        cb_coef: Optional[float] = None,
    ):
        """Constructor.

        Args:
            config (dict): the config of the trial (note that the config is a set
                because the hyperparameters are).
            min_resource_lease (float): the minimum resource lease.
            metric (str): the loss metric.
            is_champion (bool): indicates whether the trial is the current champion or not.
            is_checked_under_current_champion (bool): indicates whether this trials has
                been paused under the current champion.
            trial_id (str): id of the trial (if None, it will be generated in the constructor).
        """
        try:
            from vowpalwabbit import pyvw
        except ImportError:
            raise ImportError("To use AutoVW, please run pip install flaml[vw] to install vowpalwabbit")
        # attributes
        self.trial_id = self._config_to_id(config) if trial_id is None else trial_id
        logger.info("Create trial with trial_id: %s", self.trial_id)
        super().__init__(
            config,
            min_resource_lease,
            is_champion,
            is_checked_under_current_champion,
            custom_trial_name,
            self.trial_id,
        )
        self.model = None  # model is None until the config is scheduled to run
        self.result = None
        self.trainable_class = pyvw.vw
        # variables that are needed during online training
        self._metric = metric
        self._y_min_observed = None
        self._y_max_observed = None
        # application dependent variables
        self._dim = None
        self._cb_coef = cb_coef

    @staticmethod
    def _config_to_id(config):
        """Generate an id for the provided config."""
        # sort config keys
        sorted_k_list = sorted(list(config.keys()))
        config_id_full = ""
        for key in sorted_k_list:
            v = config[key]
            config_id = "|"
            if isinstance(v, set):
                value_list = sorted(v)
                config_id += "_".join([str(k) for k in value_list])
            else:
                config_id += str(v)
            config_id_full = config_id_full + config_id
        return config_id_full

    def _initialize_vw_model(self, vw_example):
        """Initialize a vw model using the trainable_class"""
        self._vw_config = self.config.copy()
        ns_interactions = self.config.get(VowpalWabbitTrial.interactions_config_key, None)
        # ensure the feature interaction config is a list (required by VW)
        if ns_interactions is not None:
            self._vw_config[VowpalWabbitTrial.interactions_config_key] = list(ns_interactions)
        # get the dimensionality of the feature according to the namespace configuration
        namespace_feature_dim = get_ns_feature_dim_from_vw_example(vw_example)
        self._dim = self._get_dim_from_ns(namespace_feature_dim, ns_interactions)
        # construct an instance of vw model using the input config and fixed config
        self.model = self.trainable_class(**self._vw_config)
        self.result = OnlineResult(
            self._metric,
            cb_coef=self._cb_coef,
            init_loss=0.0,
            init_cb=100.0,
        )

    def train_eval_model_online(self, data_sample, y_pred):
        """Train and evaluate model online."""
        # extract info needed the first time we see the data
        if self._resource_lease == "auto" or self._resource_lease is None:
            assert self._dim is not None
            self._resource_lease = self._dim * self.MIN_RES_CONST
        y = self._get_y_from_vw_example(data_sample)
        self._update_y_range(y)
        if self.model is None:
            # initialize self.model and self.result
            self._initialize_vw_model(data_sample)
        # do one step of learning
        self.model.learn(data_sample)
        # update training related results accordingly
        new_loss = self._get_loss(y, y_pred, self._metric, self._y_min_observed, self._y_max_observed)
        # udpate sample size, sum of loss, and cost
        data_sample_size = 1
        bound_of_range = self._y_max_observed - self._y_min_observed
        if bound_of_range == 0:
            bound_of_range = 1.0
        self.result.update_result(
            new_loss,
            VowpalWabbitTrial.cost_unit * data_sample_size,
            self._dim,
            bound_of_range,
        )

    def predict(self, x):
        """Predict using the model."""
        if self.model is None:
            # initialize self.model and self.result
            self._initialize_vw_model(x)
        return self.model.predict(x)

    def _get_loss(self, y_true, y_pred, loss_func_name, y_min_observed, y_max_observed):
        """Get instantaneous loss from y_true and y_pred, and loss_func_name
        For mae_clip, we clip y_pred in the observed range of y
        """
        if "mse" in loss_func_name or "squared" in loss_func_name:
            loss_func = mean_squared_error
        elif "mae" in loss_func_name or "absolute" in loss_func_name:
            loss_func = mean_absolute_error
            if y_min_observed is not None and y_max_observed is not None and "clip" in loss_func_name:
                # clip y_pred in the observed range of y
                y_pred = min(y_max_observed, max(y_pred, y_min_observed))
        else:
            raise NotImplementedError
        return loss_func([y_true], [y_pred])

    def _update_y_range(self, y):
        """Maintain running observed minimum and maximum target value."""
        if self._y_min_observed is None or y < self._y_min_observed:
            self._y_min_observed = y
        if self._y_max_observed is None or y > self._y_max_observed:
            self._y_max_observed = y

    @staticmethod
    def _get_dim_from_ns(namespace_feature_dim: dict, namespace_interactions: Union[set, list]):
        """Get the dimensionality of the corresponding feature of input namespace set."""
        total_dim = sum(namespace_feature_dim.values())
        if namespace_interactions:
            for f in namespace_interactions:
                ns_dim = 1.0
                for c in f:
                    ns_dim *= namespace_feature_dim[c]
                total_dim += ns_dim
        return total_dim

    def clean_up_model(self):
        self.model = None
        self.result = None

    @staticmethod
    def _get_y_from_vw_example(vw_example):
        """Get y from a vw_example. this works for regression datasets."""
        return float(vw_example.split("|")[0])
