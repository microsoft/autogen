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
from flaml.tune import trial_runner
from flaml.tune.trial import Trial


class TrialScheduler:
    """Interface for implementing a Trial Scheduler class."""

    CONTINUE = "CONTINUE"  #: Status for continuing trial execution
    PAUSE = "PAUSE"  #: Status for pausing trial execution
    STOP = "STOP"  #: Status for stopping trial execution

    def on_trial_add(self, trial_runner: "trial_runner.TrialRunner", trial: Trial):
        pass

    def on_trial_remove(self, trial_runner: "trial_runner.TrialRunner", trial: Trial):
        pass
