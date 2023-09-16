import numpy as np
import logging
from typing import Dict
from flaml.tune.scheduler import TrialScheduler
from flaml.tune import Trial

logger = logging.getLogger(__name__)


class OnlineScheduler(TrialScheduler):
    """Class for the most basic OnlineScheduler."""

    def on_trial_result(self, trial_runner, trial: Trial, result: Dict):
        """Report result and return a decision on the trial's status."""
        # Always keep a trial running (return status TrialScheduler.CONTINUE).
        return TrialScheduler.CONTINUE

    def choose_trial_to_run(self, trial_runner) -> Trial:
        """Decide which trial to run next."""
        # Trial prioritrization according to the status:
        # PENDING (trials that have not been tried) > PAUSED (trials that have been ran).
        # For trials with the same status, it chooses the ones with smaller resource lease.
        for trial in trial_runner.get_trials():
            if trial.status == Trial.PENDING:
                return trial
        min_paused_resource = np.inf
        min_paused_resource_trial = None
        for trial in trial_runner.get_trials():
            # if there is a tie, prefer the earlier added ones
            if trial.status == Trial.PAUSED and trial.resource_lease < min_paused_resource:
                min_paused_resource = trial.resource_lease
                min_paused_resource_trial = trial
        if min_paused_resource_trial is not None:
            return min_paused_resource_trial


class OnlineSuccessiveDoublingScheduler(OnlineScheduler):
    """class for the OnlineSuccessiveDoublingScheduler algorithm."""

    def __init__(self, increase_factor: float = 2.0):
        """Constructor.

        Args:
            increase_factor: A float of multiplicative factor
                used to increase resource lease. Default is 2.0.
        """
        super().__init__()
        self._increase_factor = increase_factor

    def on_trial_result(self, trial_runner, trial: Trial, result: Dict):
        """Report result and return a decision on the trial's status."""
        # 1. Returns TrialScheduler.CONTINUE (i.e., keep the trial running),
        # if the resource consumed has not reached the current resource_lease.s.
        # 2. otherwise double the current resource lease and return TrialScheduler.PAUSE.
        if trial.result is None or trial.result.resource_used < trial.resource_lease:
            return TrialScheduler.CONTINUE
        else:
            trial.set_resource_lease(trial.resource_lease * self._increase_factor)
            logger.info(
                "Doubled resource for trial %s, used: %s, current budget %s",
                trial.trial_id,
                trial.result.resource_used,
                trial.resource_lease,
            )
            return TrialScheduler.PAUSE


class ChaChaScheduler(OnlineSuccessiveDoublingScheduler):
    """class for the ChaChaScheduler algorithm."""

    def __init__(self, increase_factor: float = 2.0, **kwargs):
        """Constructor.

        Args:
            increase_factor: A float of multiplicative factor
                used to increase resource lease. Default is 2.0.
        """
        super().__init__(increase_factor)
        self._keep_champion = kwargs.get("keep_champion", True)
        self._keep_challenger_metric = kwargs.get("keep_challenger_metric", "ucb")
        self._keep_challenger_ratio = kwargs.get("keep_challenger_ratio", 0.5)
        self._pause_old_froniter = kwargs.get("pause_old_froniter", False)
        logger.info("Using chacha scheduler with config %s", kwargs)

    def on_trial_result(self, trial_runner, trial: Trial, result: Dict):
        """Report result and return a decision on the trial's status."""
        # Make a decision according to: SuccessiveDoubling + champion check + performance check.
        # Doubling scheduler makes a decision
        decision = super().on_trial_result(trial_runner, trial, result)
        # ***********Check whether the trial has been paused since a new champion is promoted**
        # NOTE: This check is not enabled by default. Just keeping it for experimentation purpose.
        ## trial.is_checked_under_current_champion being False means the trial
        # has not been paused since the new champion is promoted. If so, we need to
        # tentatively pause it such that new trials can possiblly be taken into consideration
        # NOTE: This may need to be changed. We need to do this because we only add trials.
        # into the OnlineTrialRunner when there are avaialbe slots. Maybe we need to consider
        # adding max_running_trial number of trials once a new champion is promoted.
        if self._pause_old_froniter and not trial.is_checked_under_current_champion:
            if decision == TrialScheduler.CONTINUE:
                decision = TrialScheduler.PAUSE
                trial.set_checked_under_current_champion(True)
                logger.info("Tentitively set trial as paused")

        # ****************Keep the champion always running******************
        if (
            self._keep_champion
            and trial.trial_id == trial_runner.champion_trial.trial_id
            and decision == TrialScheduler.PAUSE
        ):
            return TrialScheduler.CONTINUE

        # ****************Keep the trials with top performance always running******************
        if self._keep_challenger_ratio is not None:
            if decision == TrialScheduler.PAUSE:
                logger.debug("champion, %s", trial_runner.champion_trial.trial_id)
                # this can be inefficient when the # trials is large. TODO: need to improve efficiency.
                top_trials = trial_runner.get_top_running_trials(
                    self._keep_challenger_ratio, self._keep_challenger_metric
                )
                logger.debug("top_learners: %s", top_trials)
                if trial in top_trials:
                    logger.debug("top runner %s: set from PAUSE to CONTINUE", trial.trial_id)
                    return TrialScheduler.CONTINUE
        return decision
