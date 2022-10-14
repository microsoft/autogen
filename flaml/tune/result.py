# Copyright 2020 The Ray Authors.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This source file is adapted here because ray does not fully support Windows.

# Copyright (c) Microsoft Corporation.
import os

# yapf: disable
# __sphinx_doc_begin__
# (Optional/Auto-filled) training is terminated. Filled only if not provided.
DONE = "done"

# (Optional) Enum for user controlled checkpoint
SHOULD_CHECKPOINT = "should_checkpoint"

# (Auto-filled) The hostname of the machine hosting the training process.
HOSTNAME = "hostname"

# (Auto-filled) The auto-assigned id of the trial.
TRIAL_ID = "trial_id"

# (Auto-filled) The auto-assigned id of the trial.
EXPERIMENT_TAG = "experiment_tag"

# (Auto-filled) The node ip of the machine hosting the training process.
NODE_IP = "node_ip"

# (Auto-filled) The pid of the training process.
PID = "pid"

# (Optional) Default (anonymous) metric when using tune.report(x)
DEFAULT_METRIC = "_metric"

# (Optional) Mean reward for current training iteration
EPISODE_REWARD_MEAN = "episode_reward_mean"

# (Optional) Mean loss for training iteration
MEAN_LOSS = "mean_loss"

# (Optional) Mean loss for training iteration
NEG_MEAN_LOSS = "neg_mean_loss"

# (Optional) Mean accuracy for training iteration
MEAN_ACCURACY = "mean_accuracy"

# Number of episodes in this iteration.
EPISODES_THIS_ITER = "episodes_this_iter"

# (Optional/Auto-filled) Accumulated number of episodes for this trial.
EPISODES_TOTAL = "episodes_total"

# Number of timesteps in this iteration.
TIMESTEPS_THIS_ITER = "timesteps_this_iter"

# (Auto-filled) Accumulated number of timesteps for this entire trial.
TIMESTEPS_TOTAL = "timesteps_total"

# (Auto-filled) Time in seconds this iteration took to run.
# This may be overridden to override the system-computed time difference.
TIME_THIS_ITER_S = "time_this_iter_s"

# (Auto-filled) Accumulated time in seconds for this entire trial.
TIME_TOTAL_S = "time_total_s"

# (Auto-filled) The index of this training iteration.
TRAINING_ITERATION = "training_iteration"
# __sphinx_doc_end__
# yapf: enable

DEFAULT_EXPERIMENT_INFO_KEYS = ("trainable_name", EXPERIMENT_TAG, TRIAL_ID)

DEFAULT_RESULT_KEYS = (
    TRAINING_ITERATION,
    TIME_TOTAL_S,
    TIMESTEPS_TOTAL,
    MEAN_ACCURACY,
    MEAN_LOSS,
)

# Make sure this doesn't regress
AUTO_RESULT_KEYS = (
    TRAINING_ITERATION,
    TIME_TOTAL_S,
    EPISODES_TOTAL,
    TIMESTEPS_TOTAL,
    NODE_IP,
    HOSTNAME,
    PID,
    TIME_TOTAL_S,
    TIME_THIS_ITER_S,
    "timestamp",
    "experiment_id",
    "date",
    "time_since_restore",
    "iterations_since_restore",
    "timesteps_since_restore",
    "config",
)

# __duplicate__ is a magic keyword used internally to
# avoid double-logging results when using the Function API.
RESULT_DUPLICATE = "__duplicate__"

# __trial_info__ is a magic keyword used internally to pass trial_info
# to the Trainable via the constructor.
TRIAL_INFO = "__trial_info__"

# __stdout_file__/__stderr_file__ are magic keywords used internally
# to pass log file locations to the Trainable via the constructor.
STDOUT_FILE = "__stdout_file__"
STDERR_FILE = "__stderr_file__"

# Where Tune writes result files by default
DEFAULT_RESULTS_DIR = (
    os.environ.get("TEST_TMPDIR")
    or os.environ.get("TUNE_RESULT_DIR")
    or os.path.expanduser("~/ray_results")
)

# Meta file about status under each experiment directory, can be
# parsed by automlboard if exists.
JOB_META_FILE = "job_status.json"

# Meta file about status under each trial directory, can be parsed
# by automlboard if exists.
EXPR_META_FILE = "trial_status.json"

# File that stores parameters of the trial.
EXPR_PARAM_FILE = "params.json"

# Pickle File that stores parameters of the trial.
EXPR_PARAM_PICKLE_FILE = "params.pkl"

# File that stores the progress of the trial.
EXPR_PROGRESS_FILE = "progress.csv"

# File that stores results of the trial.
EXPR_RESULT_FILE = "result.json"

# Config prefix when using Analysis.
CONFIG_PREFIX = "config/"
