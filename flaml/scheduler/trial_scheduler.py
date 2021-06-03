'''
Copyright 2020 The Ray Authors.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

This source file is adapted here because ray does not fully support Windows.

Copyright (c) Microsoft Corporation.
'''
from typing import Dict, Optional

from flaml.tune import trial_runner
from flaml.tune.result import DEFAULT_METRIC
from flaml.tune.trial import Trial


class TrialScheduler:
    """Interface for implementing a Trial Scheduler class."""

    CONTINUE = "CONTINUE"  #: Status for continuing trial execution
    PAUSE = "PAUSE"  #: Status for pausing trial execution
    STOP = "STOP"  #: Status for stopping trial execution

    _metric = None

    @property
    def metric(self):
        return self._metric

    def set_search_properties(self, metric: Optional[str],
                              mode: Optional[str]) -> bool:
        """Pass search properties to scheduler.
        This method acts as an alternative to instantiating schedulers
        that react to metrics with their own `metric` and `mode` parameters.
        Args:
            metric (str): Metric to optimize
            mode (str): One of ["min", "max"]. Direction to optimize.
        """
        if self._metric and metric:
            return False
        if metric:
            self._metric = metric

        if self._metric is None:
            # Per default, use anonymous metric
            self._metric = DEFAULT_METRIC

        return True

    def on_trial_add(self, trial_runner: "trial_runner.TrialRunner",
                     trial: Trial):
        """Called when a new trial is added to the trial runner."""

        raise NotImplementedError

    def on_trial_error(self, trial_runner: "trial_runner.TrialRunner",
                       trial: Trial):
        """Notification for the error of trial.
        This will only be called when the trial is in the RUNNING state."""

        raise NotImplementedError

    def on_trial_result(self, trial_runner: "trial_runner.TrialRunner",
                        trial: Trial, result: Dict) -> str:
        """Called on each intermediate result returned by a trial.
        At this point, the trial scheduler can make a decision by returning
        one of CONTINUE, PAUSE, and STOP. This will only be called when the
        trial is in the RUNNING state."""

        raise NotImplementedError

    def on_trial_complete(self, trial_runner: "trial_runner.TrialRunner",
                          trial: Trial, result: Dict):
        """Notification for the completion of trial.
        This will only be called when the trial is in the RUNNING state and
        either completes naturally or by manual termination."""

        raise NotImplementedError

    def on_trial_remove(self, trial_runner: "trial_runner.TrialRunner",
                        trial: Trial):
        """Called to remove trial.
        This is called when the trial is in PAUSED or PENDING state. Otherwise,
        call `on_trial_complete`."""

        raise NotImplementedError

    def choose_trial_to_run(
            self, trial_runner: "trial_runner.TrialRunner") -> Optional[Trial]:
        """Called to choose a new trial to run.
        This should return one of the trials in trial_runner that is in
        the PENDING or PAUSED state. This function must be idempotent.
        If no trial is ready, return None."""

        raise NotImplementedError

    def debug_string(self) -> str:
        """Returns a human readable message for printing to the console."""

        raise NotImplementedError

    def save(self, checkpoint_path: str):
        """Save trial scheduler to a checkpoint"""
        raise NotImplementedError

    def restore(self, checkpoint_path: str):
        """Restore trial scheduler from checkpoint."""
        raise NotImplementedError


class FIFOScheduler(TrialScheduler):
    """Simple scheduler that just runs trials in submission order."""

    def on_trial_add(self, trial_runner: "trial_runner.TrialRunner",
                     trial: Trial):
        pass

    def on_trial_error(self, trial_runner: "trial_runner.TrialRunner",
                       trial: Trial):
        pass

    def on_trial_result(self, trial_runner: "trial_runner.TrialRunner",
                        trial: Trial, result: Dict) -> str:
        return TrialScheduler.CONTINUE

    def on_trial_complete(self, trial_runner: "trial_runner.TrialRunner",
                          trial: Trial, result: Dict):
        pass

    def on_trial_remove(self, trial_runner: "trial_runner.TrialRunner",
                        trial: Trial):
        pass

    def choose_trial_to_run(
            self, trial_runner: "trial_runner.TrialRunner") -> Optional[Trial]:
        for trial in trial_runner.get_trials():
            if (trial.status == Trial.PENDING
                    and trial_runner.has_resources_for_trial(trial)):
                return trial
        for trial in trial_runner.get_trials():
            if (trial.status == Trial.PAUSED
                    and trial_runner.has_resources_for_trial(trial)):
                return trial
        return None

    def debug_string(self) -> str:
        return "Using FIFO scheduling algorithm."
