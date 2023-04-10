import numpy as np
import math
from flaml.tune import Trial
from flaml.tune.scheduler import TrialScheduler

import logging

logger = logging.getLogger(__name__)


class OnlineTrialRunner:
    """Class for the OnlineTrialRunner."""

    # ************NOTE about the status of a trial***************
    # Trial.PENDING: All trials are set to be pending when frist added into the OnlineTrialRunner until
    #     it is selected to run. By this definition, a trial with status Trial.PENDING is a challenger
    #     trial added to the OnlineTrialRunner but never been selected to run.
    #     It denotes the starting of trial's lifespan in the OnlineTrialRunner.
    # Trial.RUNNING: It indicates that this trial is one of the concurrently running trials.
    #     The max number of Trial.RUNNING trials is running_budget.
    #     The status of a trial will be set to Trial.RUNNING the next time it selected to run.
    #     A trial's status may have the following change:
    #     Trial.PENDING -> Trial.RUNNING
    #     Trial.PAUSED - > Trial.RUNNING
    # Trial.PAUSED: The status of a trial is set to Trial.PAUSED once it is removed from the running trials.
    #     Trial.RUNNING - > Trial.PAUSED
    # Trial.TERMINATED: set the status of a trial to Trial.TERMINATED when you never want to select it.
    #     It denotes the real end of a trial's lifespan.
    # Status change routine of a trial:
    # Trial.PENDING -> (Trial.RUNNING -> Trial.PAUSED -> Trial.RUNNING -> ...) -> Trial.TERMINATED(optional)

    RANDOM_SEED = 123456
    WARMSTART_NUM = 100

    def __init__(
        self, max_live_model_num: int, searcher=None, scheduler=None, champion_test_policy="loss_ucb", **kwargs
    ):
        """Constructor.

        Args:
            max_live_model_num: The maximum number of 'live'/running models allowed.
            searcher: A class for generating Trial objects progressively.
                The ConfigOracle is implemented in the searcher.
            scheduler: A class for managing the 'live' trials and allocating the
                resources for the trials.
            champion_test_policy: A string to specify what test policy to test for
                champion. Currently can choose from ['loss_ucb', 'loss_avg', 'loss_lcb', None].
        """
        # ************A NOTE about the input searcher and scheduler******
        # Required methods of the searcher:
        # - next_trial()
        #     Generate the next trial to add.
        # - set_search_properties(metric: Optional[str], mode: Optional[str],
        #                         config: Optional[dict], setting: Optional[dict])
        #     Generate new challengers based on the current champion and update the challenger list
        # - on_trial_result(trial_id: str, result: Dict)
        #     Reprot results to the scheduler.
        # Required methods of the scheduler:
        # - on_trial_add(trial_runner, trial: Trial)
        #     It adds candidate trials to the scheduler. It is called inside of the add_trial
        #     function in the TrialRunner.
        # - on_trial_remove(trial_runner, trial: Trial)
        #     Remove terminated trials from the scheduler.
        # - on_trial_result(trial_runner, trial: Trial, result: Dict)
        #     Reprot results to the scheduler.
        # - choose_trial_to_run(trial_runner) -> Optional[Trial]
        # Among them, on_trial_result and choose_trial_to_run are the most important methods
        # *****************************************************************
        # OnlineTrialRunner setting
        self._searcher = searcher
        self._scheduler = scheduler
        self._champion_test_policy = champion_test_policy
        self._max_live_model_num = max_live_model_num
        self._remove_worse = kwargs.get("remove_worse", True)
        self._bound_trial_num = kwargs.get("bound_trial_num", False)
        self._no_model_persistence = True

        # stores all the trials added to the OnlineTrialRunner
        # i.e., include the champion and all the challengers
        self._trials = []
        self._champion_trial = None
        self._best_challenger_trial = None
        self._first_challenger_pool_size = None
        self._random_state = np.random.RandomState(self.RANDOM_SEED)
        self._running_trials = set()

        # initially schedule up to max_live_model_num of live models and
        # set the first trial as the champion (which is done inside self.step())
        self._total_steps = 0
        logger.info("init step %s", self._max_live_model_num)
        # TODO: add more comments
        self.step()
        assert self._champion_trial is not None

    @property
    def champion_trial(self) -> Trial:
        """The champion trial."""
        return self._champion_trial

    @property
    def running_trials(self):
        """The running/'live' trials."""
        return self._running_trials

    def step(self, data_sample=None, prediction_trial_tuple=None):
        """Schedule one trial to run each time it is called.

        Args:
            data_sample: One data example.
            prediction_trial_tuple: A list of information containing
                (prediction_made, prediction_trial).
        """
        # TODO: Will remove prediction_trial_tuple.
        # NOTE: This function consists of the following several parts:
        # * Update model:
        # 0. Update running trials using observations received.
        # * Tests for Champion:
        # 1. Test for champion (BetterThan test, and WorseThan test)
        #     1.1 BetterThan test
        #     1.2 WorseThan test: a trial may be removed if WroseThan test is triggered
        # * Online Scheduling:
        # 2. Report results to the searcher and scheduler (the scheduler will return a decision about
        #     the status of the running trials).
        # 3. Pause or stop a trial according to the scheduler's decision.
        # Add a trial into the OnlineTrialRunner if there are opening slots.

        # ***********Update running trials with observation*******************
        if data_sample is not None:
            self._total_steps += 1
            prediction_made, prediction_trial = (
                prediction_trial_tuple[0],
                prediction_trial_tuple[1],
            )
            # assert prediction_trial.status == Trial.RUNNING
            trials_to_pause = []
            for trial in list(self._running_trials):
                if trial != prediction_trial:
                    y_predicted = trial.predict(data_sample)
                else:
                    y_predicted = prediction_made
                trial.train_eval_model_online(data_sample, y_predicted)
                logger.debug(
                    "running trial at iter %s %s %s %s %s %s",
                    self._total_steps,
                    trial.trial_id,
                    trial.result.loss_avg,
                    trial.result.loss_cb,
                    trial.result.resource_used,
                    trial.resource_lease,
                )
                # report result to the searcher
                self._searcher.on_trial_result(trial.trial_id, trial.result)
                # report result to the scheduler and the scheduler makes a decision about
                # the running status of the trial
                decision = self._scheduler.on_trial_result(self, trial, trial.result)
                # set the status of the trial according to the decision made by the scheduler
                logger.debug(
                    "trial decision %s %s at step %s",
                    decision,
                    trial.trial_id,
                    self._total_steps,
                )
                if decision == TrialScheduler.STOP:
                    self.stop_trial(trial)
                elif decision == TrialScheduler.PAUSE:
                    trials_to_pause.append(trial)
                else:
                    self.run_trial(trial)
            # ***********Statistical test of champion*************************************
            self._champion_test()
            # Pause the trial after the tests because the tests involves the reset of the trial's result
            for trial in trials_to_pause:
                self.pause_trial(trial)
        # ***********Add and schedule new trials to run if there are opening slots****
        # Add trial if needed: add challengers into consideration through _add_trial_from_searcher()
        # if there are available slots
        for _ in range(self._max_live_model_num - len(self._running_trials)):
            self._add_trial_from_searcher()
        # Scheduling: schedule up to max_live_model_num number of trials to run
        # (set the status as Trial.RUNNING)
        while self._max_live_model_num > len(self._running_trials):
            trial_to_run = self._scheduler.choose_trial_to_run(self)
            if trial_to_run is not None:
                self.run_trial(trial_to_run)
            else:
                break

    def get_top_running_trials(self, top_ratio=None, top_metric="ucb") -> list:
        """Get a list of trial ids, whose performance is among the top running trials."""
        running_valid_trials = [trial for trial in self._running_trials if trial.result is not None]
        if not running_valid_trials:
            return
        if top_ratio is None:
            top_number = 0
        elif isinstance(top_ratio, float):
            top_number = math.ceil(len(running_valid_trials) * top_ratio)
        elif isinstance(top_ratio, str) and "best" in top_ratio:
            top_number = 1
        else:
            raise NotImplementedError

        if "ucb" in top_metric:
            test_attribute = "loss_ucb"
        elif "avg" in top_metric:
            test_attribute = "loss_avg"
        elif "lcb" in top_metric:
            test_attribute = "loss_lcb"
        else:
            raise NotImplementedError
        top_running_valid_trials = []
        logger.info("Running trial ids %s", [trial.trial_id for trial in running_valid_trials])
        self._random_state.shuffle(running_valid_trials)
        results = [trial.result.get_score(test_attribute) for trial in running_valid_trials]
        # sorted result (small to large) index
        sorted_index = np.argsort(np.array(results))
        for i in range(min(top_number, len(running_valid_trials))):
            top_running_valid_trials.append(running_valid_trials[sorted_index[i]])
        logger.info("Top running ids %s", [trial.trial_id for trial in top_running_valid_trials])
        return top_running_valid_trials

    def _add_trial_from_searcher(self):
        """Add a new trial to this TrialRunner.

        NOTE:
            The new trial is acquired from the input search algorithm, i.e. self._searcher.
            A 'new' trial means the trial is not in self._trial.
        """
        # (optionally) upper bound the number of trials in the OnlineTrialRunner
        if self._bound_trial_num and self._first_challenger_pool_size is not None:
            active_trial_size = len([t for t in self._trials if t.status != Trial.TERMINATED])
            trial_num_upper_bound = (
                int(round((np.log10(self._total_steps) + 1) * self._first_challenger_pool_size))
                if self._first_challenger_pool_size
                else np.inf
            )
            if active_trial_size > trial_num_upper_bound:
                logger.info(
                    "Not adding new trials: %s exceeds trial limit %s.",
                    active_trial_size,
                    trial_num_upper_bound,
                )
                return None

        # output one trial from the trial pool (new challenger pool) maintained in the searcher
        # Assumption on the searcher: when all frontiers (i.e., all the challengers generated
        # based on the current champion) of the current champion are added, calling next_trial()
        # will return None
        trial = self._searcher.next_trial()
        if trial is not None:
            self.add_trial(trial)  # dup checked in add_trial
            # the champion_trial is initially None, so we need to set it up the first time
            # a valid trial is added.
            # Assumption on self._searcher: the first trial generated is the champion trial
            if self._champion_trial is None:
                logger.info("Initial set up of the champion trial %s", trial.config)
                self._set_champion(trial)
        else:
            self._all_new_challengers_added = True
            if self._first_challenger_pool_size is None:
                self._first_challenger_pool_size = len(self._trials)

    def _champion_test(self):
        """Perform tests again the latest champion, including bette_than tests and worse_than tests"""
        # for BetterThan test, we only need to compare the best challenger with the champion
        self._get_best_challenger()
        if self._best_challenger_trial is not None:
            assert self._best_challenger_trial.trial_id != self._champion_trial.trial_id
            # test whether a new champion is found and set the trial properties accordingly
            is_new_champion_found = self._better_than_champion_test(self._best_challenger_trial)
            if is_new_champion_found:
                self._set_champion(new_champion_trial=self._best_challenger_trial)

        # performs _worse_than_champion_test, which is an optional component in ChaCha
        if self._remove_worse:
            to_stop = []
            for trial_to_test in self._trials:
                if trial_to_test.status != Trial.TERMINATED:
                    worse_than_champion = self._worse_than_champion_test(
                        self._champion_trial, trial_to_test, self.WARMSTART_NUM
                    )
                    if worse_than_champion:
                        to_stop.append(trial_to_test)
            # we want to ensure there are at least #max_live_model_num of challengers remaining
            max_to_stop_num = len([t for t in self._trials if t.status != Trial.TERMINATED]) - self._max_live_model_num
            for i in range(min(max_to_stop_num, len(to_stop))):
                self.stop_trial(to_stop[i])

    def _get_best_challenger(self):
        """Get the 'best' (in terms of the champion_test_policy) challenger under consideration."""
        if self._champion_test_policy is None:
            return
        if "ucb" in self._champion_test_policy:
            test_attribute = "loss_ucb"
        elif "avg" in self._champion_test_policy:
            test_attribute = "loss_avg"
        else:
            raise NotImplementedError
        active_trials = [
            trial
            for trial in self._trials
            if (
                trial.status != Trial.TERMINATED
                and trial.trial_id != self._champion_trial.trial_id
                and trial.result is not None
            )
        ]
        if active_trials:
            self._random_state.shuffle(active_trials)
            results = [trial.result.get_score(test_attribute) for trial in active_trials]
            best_index = np.argmin(results)
            self._best_challenger_trial = active_trials[best_index]

    def _set_champion(self, new_champion_trial):
        """Set the status of the existing trials once a new champion is found."""
        assert new_champion_trial is not None
        is_init_update = False
        if self._champion_trial is None:
            is_init_update = True
        self.run_trial(new_champion_trial)
        # set the checked_under_current_champion status of the trials
        for trial in self._trials:
            if trial.trial_id == new_champion_trial.trial_id:
                trial.set_checked_under_current_champion(True)
            else:
                trial.set_checked_under_current_champion(False)
        self._champion_trial = new_champion_trial
        self._all_new_challengers_added = False
        logger.info("Set the champion as %s", self._champion_trial.trial_id)
        if not is_init_update:
            self._champion_update_times += 1
            # calling set_search_properties of searcher will trigger
            # new challenger generation. we do not do this for init champion
            # as this step is already done when first constructing the searcher
            self._searcher.set_search_properties(setting={self._searcher.CHAMPION_TRIAL_NAME: self._champion_trial})
        else:
            self._champion_update_times = 0

    def get_trials(self) -> list:
        """Return the list of trials managed by this TrialRunner."""
        return self._trials

    def add_trial(self, new_trial):
        """Add a new trial to this TrialRunner.
        Trials may be added at any time.

        Args:
            new_trial (Trial): Trial to queue.
        """
        # Only add the new trial when it does not exist (according to the trial_id, which is
        # the signature of the trail) in self._trials.
        for trial in self._trials:
            if trial.trial_id == new_trial.trial_id:
                trial.set_checked_under_current_champion(True)
                return
        logger.info(
            "adding trial at iter %s, %s %s",
            self._total_steps,
            new_trial.trial_id,
            len(self._trials),
        )
        self._trials.append(new_trial)
        self._scheduler.on_trial_add(self, new_trial)

    def stop_trial(self, trial):
        """Stop a trial: set the status of a trial to be
        Trial.TERMINATED and perform other subsequent operations.
        """
        if trial.status in [Trial.ERROR, Trial.TERMINATED]:
            return
        else:
            logger.info(
                "Terminating trial %s, with trial result %s",
                trial.trial_id,
                trial.result,
            )
            trial.set_status(Trial.TERMINATED)
            # clean up model and result
            trial.clean_up_model()
            self._scheduler.on_trial_remove(self, trial)
            self._searcher.on_trial_complete(trial.trial_id)
            self._running_trials.remove(trial)

    def pause_trial(self, trial):
        """Pause a trial: set the status of a trial to be Trial.PAUSED
        and perform other subsequent operations.
        """
        if trial.status in [Trial.ERROR, Trial.TERMINATED]:
            return
        else:
            logger.info(
                "Pausing trial %s, with trial loss_avg: %s, loss_cb: %s, loss_ucb: %s,\
                        resource_lease: %s",
                trial.trial_id,
                trial.result.loss_avg,
                trial.result.loss_cb,
                trial.result.loss_avg + trial.result.loss_cb,
                trial.resource_lease,
            )
            trial.set_status(Trial.PAUSED)
            # clean up model and result if no model persistence
            if self._no_model_persistence:
                trial.clean_up_model()
            self._running_trials.remove(trial)

    def run_trial(self, trial):
        """Run a trial: set the status of a trial to be Trial.RUNNING
        and perform other subsequent operations.
        """
        if trial.status in [Trial.ERROR, Trial.TERMINATED]:
            return
        else:
            trial.set_status(Trial.RUNNING)
            self._running_trials.add(trial)

    def _better_than_champion_test(self, trial_to_test):
        """Test whether there is a config in the existing trials that
        is better than the current champion config.

        Returns:
            A bool indicating whether a new champion is found.
        """
        if trial_to_test.result is not None and self._champion_trial.result is not None:
            if "ucb" in self._champion_test_policy:
                return self._test_lcb_ucb(self._champion_trial, trial_to_test, self.WARMSTART_NUM)
            elif "avg" in self._champion_test_policy:
                return self._test_avg_loss(self._champion_trial, trial_to_test, self.WARMSTART_NUM)
            elif "martingale" in self._champion_test_policy:
                return self._test_martingale(self._champion_trial, trial_to_test)
            else:
                raise NotImplementedError
        else:
            return False

    @staticmethod
    def _worse_than_champion_test(champion_trial, trial, warmstart_num=1) -> bool:
        """Test whether the input trial is worse than the champion_trial"""
        if trial.result is not None and trial.result.resource_used >= warmstart_num:
            if trial.result.loss_lcb > champion_trial.result.loss_ucb:
                logger.info(
                    "=========trial %s is worse than champion %s=====",
                    trial.trial_id,
                    champion_trial.trial_id,
                )
                logger.info("trial %s %s %s", trial.config, trial.result, trial.resource_lease)
                logger.info(
                    "trial loss_avg:%s, trial loss_cb %s",
                    trial.result.loss_avg,
                    trial.result.loss_cb,
                )
                logger.info(
                    "champion loss_avg:%s, champion loss_cb %s",
                    champion_trial.result.loss_avg,
                    champion_trial.result.loss_cb,
                )
                logger.info("champion %s", champion_trial.config)
                logger.info(
                    "trial loss_avg_recent:%s, trial loss_cb %s",
                    trial.result.loss_avg_recent,
                    trial.result.loss_cb,
                )
                logger.info(
                    "champion loss_avg_recent:%s, champion loss_cb %s",
                    champion_trial.result.loss_avg_recent,
                    champion_trial.result.loss_cb,
                )
                return True
        return False

    @staticmethod
    def _test_lcb_ucb(champion_trial, trial, warmstart_num=1) -> bool:
        """Comare the challenger(i.e., trial)'s loss upper bound with
        champion_trial's loss lower bound - cb
        """
        assert trial.trial_id != champion_trial.trial_id
        if trial.result.resource_used >= warmstart_num:
            if trial.result.loss_ucb < champion_trial.result.loss_lcb - champion_trial.result.loss_cb:
                logger.info("======new champion condition satisfied: using lcb vs ucb=====")
                logger.info(
                    "new champion trial %s %s %s",
                    trial.trial_id,
                    trial.result.resource_used,
                    trial.resource_lease,
                )
                logger.info(
                    "new champion trial loss_avg:%s, trial loss_cb %s",
                    trial.result.loss_avg,
                    trial.result.loss_cb,
                )
                logger.info(
                    "old champion trial %s %s %s",
                    champion_trial.trial_id,
                    champion_trial.result.resource_used,
                    champion_trial.resource_lease,
                )
                logger.info(
                    "old champion loss avg %s, loss cb %s",
                    champion_trial.result.loss_avg,
                    champion_trial.result.loss_cb,
                )
                return True
        return False

    @staticmethod
    def _test_avg_loss(champion_trial, trial, warmstart_num=1) -> bool:
        """Comare the challenger(i.e., trial)'s average loss with the
        champion_trial's average loss
        """
        assert trial.trial_id != champion_trial.trial_id
        if trial.result.resource_used >= warmstart_num:
            if trial.result.loss_avg < champion_trial.result.loss_avg:
                logger.info("=====new champion condition satisfied using avg loss=====")
                logger.info("trial %s", trial.config)
                logger.info(
                    "trial loss_avg:%s, trial loss_cb %s",
                    trial.result.loss_avg,
                    trial.result.loss_cb,
                )
                logger.info(
                    "champion loss_avg:%s, champion loss_cb %s",
                    champion_trial.result.loss_avg,
                    champion_trial.result.loss_cb,
                )
                logger.info("champion %s", champion_trial.config)
                return True
        return False

    @staticmethod
    def _test_martingale(champion_trial, trial):
        """Comare the challenger and champion using confidence sequence based
        test martingale

        Not implementated yet
        """
        NotImplementedError
