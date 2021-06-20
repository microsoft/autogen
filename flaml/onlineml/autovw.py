from typing import Optional, Union
import logging
from flaml.tune import Trial, Categorical, Float, PolynomialExpansionSet, polynomial_expansion_set
from flaml.onlineml import OnlineTrialRunner
from flaml.scheduler import ChaChaScheduler
from flaml.searcher import ChampionFrontierSearcher
from flaml.onlineml.trial import get_ns_feature_dim_from_vw_example

logger = logging.getLogger(__name__)


class AutoVW:
    """The AutoML class
    """

    WARMSTART_NUM = 100
    AUTOMATIC = '_auto'
    VW_INTERACTION_ARG_NAME = 'interactions'

    def __init__(self,
                 max_live_model_num: int,
                 search_space: dict,
                 init_config: Optional[dict] = {},
                 min_resource_lease: Optional[Union[str, float]] = 'auto',
                 automl_runner_args: Optional[dict] = {},
                 scheduler_args: Optional[dict] = {},
                 model_select_policy: Optional[str] = 'threshold_loss_ucb',
                 metric: Optional[str] = 'mae_clipped',
                 random_seed: Optional[int] = None,
                 model_selection_mode: Optional[str] = 'min',
                 cb_coef: Optional[float] = None,
                 ):
        """Constructor

        Args:
            max_live_model_num: The maximum number of 'live' models, which, in other words,
                is the maximum number of models allowed to update in each learning iteraction.
            search_space: A dictionary of the search space. This search space includes both
                hyperparameters we want to tune and fixed hyperparameters. In the latter case,
                the value is a fixed value.
            init_config: A dictionary of a partial or full initial config,
                e.g. {'interactions': set(), 'learning_rate': 0.5}
            min_resource_lease: The minimum resource lease assigned to a particular model/trial.
                If set as 'auto', it will be calculated automatically.
            automl_runner_args: A dictionary of configuration for the OnlineTrialRunner.
                If set {}, default values will be used, which is equivalent to using the following configs.
                automl_runner_args =
                    {"champion_test_policy": 'loss_ucb' # specifcies how to do the statistic test for a better champion
                    "remove_worse": False              # specifcies whether to do worse than test
                    }
            scheduler_args: A dictionary of configuration for the scheduler.
                If set {}, default values will be used, which is equivalent to using the following configs.
                scheduler_args =
                    {"keep_challenger_metric": 'ucb' # what metric to use when deciding the top performing challengers
                    "keep_challenger_ratio": 0.5     # denotes the ratio of top performing challengers to keep live
                    "keep_champion": True            # specifcies whether to keep the champion always running
                    }
            model_select_policy: A string in ['threshold_loss_ucb', 'threshold_loss_lcb', 'threshold_loss_avg',
                'loss_ucb', 'loss_lcb', 'loss_avg'] to specify how to select one model to do prediction
                from the live model pool. Default value is 'threshold_loss_ucb'.
            metric: A string in ['mae_clipped', 'mae', 'mse', 'absolute_clipped', 'absolute', 'squared']
                to specify the name of the loss function used for calculating the progressive validation loss in ChaCha.
            random_seed (int): An integer of the random seed used in the searcher
                (more specifically this the random seed for ConfigOracle)
            model_selection_mode: A string in ['min', 'max'] to specify the objective as
                minimization or maximization.
            cb_coef (float): A float coefficient (optional) used in the sample complexity bound.
        """
        self._max_live_model_num = max_live_model_num
        self._search_space = search_space
        self._init_config = init_config
        self._online_trial_args = {"metric": metric,
                                   "min_resource_lease": min_resource_lease,
                                   "cb_coef": cb_coef,
                                   }
        self._automl_runner_args = automl_runner_args
        self._scheduler_args = scheduler_args
        self._model_select_policy = model_select_policy
        self._model_selection_mode = model_selection_mode
        self._random_seed = random_seed
        self._trial_runner = None
        self._best_trial = None
        # code for debugging purpose
        self._prediction_trial_id = None
        self._iter = 0

    def _setup_trial_runner(self, vw_example):
        """Set up the _trial_runner based on one vw_example
        """
        # setup the default search space for the namespace interaction hyperparameter
        search_space = self._search_space.copy()
        for k, v in self._search_space.items():
            if k == self.VW_INTERACTION_ARG_NAME and v == self.AUTOMATIC:
                raw_namespaces = self.get_ns_feature_dim_from_vw_example(vw_example).keys()
                search_space[k] = polynomial_expansion_set(init_monomials=set(raw_namespaces))
        # setup the init config based on the input _init_config and search space
        init_config = self._init_config.copy()
        for k, v in search_space.items():
            if k not in init_config.keys():
                if isinstance(v, PolynomialExpansionSet):
                    init_config[k] = set()
                elif (not isinstance(v, Categorical) and not isinstance(v, Float)):
                    init_config[k] = v
        searcher_args = {"init_config": init_config,
                         "space": search_space,
                         "random_seed": self._random_seed,
                         'online_trial_args': self._online_trial_args,
                         }
        logger.info("original search_space %s", self._search_space)
        logger.info("original init_config %s", self._init_config)
        logger.info('searcher_args %s', searcher_args)
        logger.info('scheduler_args %s', self._scheduler_args)
        logger.info('automl_runner_args %s', self._automl_runner_args)
        searcher = ChampionFrontierSearcher(**searcher_args)
        scheduler = ChaChaScheduler(**self._scheduler_args)
        self._trial_runner = OnlineTrialRunner(max_live_model_num=self._max_live_model_num,
                                               searcher=searcher,
                                               scheduler=scheduler,
                                               **self._automl_runner_args)

    def predict(self, data_sample):
        """Predict on the input example (e.g., vw example)

        Args:
            data_sample (vw_example)
        """
        if self._trial_runner is None:
            self._setup_trial_runner(data_sample)
        self._best_trial = self._select_best_trial()
        self._y_predict = self._best_trial.predict(data_sample)
        # code for debugging purpose
        if self._prediction_trial_id is None or \
                self._prediction_trial_id != self._best_trial.trial_id:
            self._prediction_trial_id = self._best_trial.trial_id
            logger.info('prediction trial id changed to %s at iter %s, resource used: %s',
                        self._prediction_trial_id, self._iter,
                        self._best_trial.result.resource_used)
        return self._y_predict

    def learn(self, data_sample):
        """Perform one online learning step with the given data sample

        Args:
            data_sample (vw_example): one data sample on which the model gets updated
        """
        self._iter += 1
        self._trial_runner.step(data_sample, (self._y_predict, self._best_trial))

    def _select_best_trial(self):
        """Select a best trial from the running trials accoring to the _model_select_policy
        """
        best_score = float('+inf') if self._model_selection_mode == 'min' else float('-inf')
        new_best_trial = None
        for trial in self._trial_runner.running_trials:
            if trial.result is not None and ('threshold' not in self._model_select_policy
                                             or trial.result.resource_used >= self.WARMSTART_NUM):
                score = trial.result.get_score(self._model_select_policy)
                if ('min' == self._model_selection_mode and score < best_score) or \
                        ('max' == self._model_selection_mode and score > best_score):
                    best_score = score
                    new_best_trial = trial
        if new_best_trial is not None:
            logger.debug('best_trial resource used: %s', new_best_trial.result.resource_used)
            return new_best_trial
        else:
            # This branch will be triggered when the resource consumption all trials are smaller
            # than the WARMSTART_NUM threshold. In this case, we will select the _best_trial
            # selected in the previous iteration.
            if self._best_trial is not None and self._best_trial.status == Trial.RUNNING:
                logger.debug('old best trial %s', self._best_trial.trial_id)
                return self._best_trial
            else:
                # this will be triggered in the first iteration or in the iteration where we want
                # to select the trial from the previous iteration but that trial has been paused
                # (i.e., self._best_trial.status != Trial.RUNNING) by the scheduler.
                logger.debug('using champion trial: %s',
                             self._trial_runner.champion_trial.trial_id)
                return self._trial_runner.champion_trial

    @staticmethod
    def get_ns_feature_dim_from_vw_example(vw_example) -> dict:
        """Get a dictionary of feature dimensionality for each namespace singleton
        """
        return get_ns_feature_dim_from_vw_example(vw_example)
