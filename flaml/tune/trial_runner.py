'''!
 * Copyright (c) 2020-2021 Microsoft Corporation. All rights reserved.
 * Licensed under the MIT License. See LICENSE file in the
 * project root for license information.
'''
from typing import Optional
try:
    from ray.tune.trial import Trial
except ImportError:
    from .trial import Trial
import logging
logger = logging.getLogger(__name__)


class Nologger():
    '''Logger without logging
    '''

    def on_result(self, result):
        pass


class SimpleTrial(Trial):
    '''A simple trial class
    '''

    def __init__(self, config, trial_id=None):
        self.trial_id = Trial.generate_id() if trial_id is None else trial_id
        self.config = config or {}
        self.status = Trial.PENDING
        self.start_time = None
        self.last_result = {}
        self.last_update_time = -float("inf")
        self.custom_trial_name = None
        self.trainable_name = "trainable"
        self.experiment_tag = "exp"
        self.verbose = False
        self.result_logger = Nologger()
        self.metric_analysis = {}
        self.n_steps = [5, 10]
        self.metric_n_steps = {}


class BaseTrialRunner:
    """Implementation of a simple trial runner

    Note that the caller usually should not mutate trial state directly.
    """

    def __init__(self,
                 search_alg=None, scheduler=None,
                 metric: Optional[str] = None,
                 mode: Optional[str] = 'min'):
        self._search_alg = search_alg
        self._scheduler_alg = scheduler
        self._trials = []
        self._metric = metric
        self._mode = mode

    def get_trials(self):
        """Returns the list of trials managed by this TrialRunner.

        Note that the caller usually should not mutate trial state directly.
        """
        return self._trials

    def add_trial(self, trial):
        """Adds a new trial to this TrialRunner.

        Trials may be added at any time.

        Args:
            trial (Trial): Trial to queue.
        """
        self._trials.append(trial)
        if self._scheduler_alg:
            self._scheduler_alg.on_trial_add(self, trial)

    def process_trial_result(self, trial, result):
        trial.update_last_result(result)
        self._search_alg.on_trial_result(trial.trial_id, result)
        if self._scheduler_alg:
            decision = self._scheduler_alg.on_trial_result(self, trial, result)
            if decision == "STOP":
                trial.set_status(Trial.TERMINATED)
            elif decision == "PAUSE":
                trial.set_status(Trial.PAUSED)

    def stop_trial(self, trial):
        """Stops trial.
        """
        if trial.status not in [Trial.ERROR, Trial.TERMINATED]:
            if self._scheduler_alg:
                self._scheduler_alg.on_trial_complete(
                    self, trial.trial_id, trial.last_result)
            self._search_alg.on_trial_complete(trial.trial_id, trial.last_result)
            trial.set_status(Trial.TERMINATED)
        elif self._scheduler_alg:
            self._scheduler_alg.on_trial_remove(self, trial)


class SequentialTrialRunner(BaseTrialRunner):
    """Implementation of the sequential trial runner
    """

    def step(self) -> Trial:
        """Runs one step of the trial event loop.
        Callers should typically run this method repeatedly in a loop. They
        may inspect or modify the runner's state in between calls to step().

        returns a Trial to run
        """
        trial_id = Trial.generate_id()
        config = self._search_alg.suggest(trial_id)
        if config:
            trial = SimpleTrial(config, trial_id)
            self.add_trial(trial)
            trial.set_status(Trial.RUNNING)
        else:
            trial = None
        self.running_trial = trial
        return trial
