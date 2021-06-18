import os
import subprocess
import hashlib
from time import time
import json


class WandbUtils:

    # Documentation on the wandb setting:
    # There are two ways to initialize wandb in tune.run:
    # (1) using WandbLoggerCallback, by adding the following argument to tune.run:
    #     callbacks=[WandbLoggerCallback(
    #                  project="hpo",
    #                  api_key = os.environ["WANDB_API_KEY"],
    #                  group = os.environ["WANDB_RUN_GROUP"],
    #                  log_config=True)]
    # (2) using wandb_mixin decorator (the current implementation)
    # The current implementation uses (2) because (1) has the following bug.
    # In Ray 1.2, when using WandbLoggerCallback + setting time limit using the time_budget_s argument,
    # A bug exists which is the previous run will not clear the cache after tune.run returns. After the
    # later run has already starts, some zombie trials in the previous run remain in the memory and never stop.
    # This bug can be reproduced by switching to (1) by adding the above callbacks argument
    # and removing the wandb_mixin decorator
    # https://docs.ray.io/en/master/tune/tutorials/tune-wandb.html

    def __init__(self,
                 is_wandb_on=False,
                 wandb_key_path=None,
                 jobid_config=None):
        if is_wandb_on:
            wandb_key = WandbUtils.get_wandb_key(wandb_key_path)
            if wandb_key != "":
                subprocess.run(["wandb", "login", "--relogin", wandb_key])
            os.environ["WANDB_API_KEY"] = wandb_key
            os.environ["WANDB_MODE"] = "online"
        else:
            os.environ["WANDB_MODE"] = "disabled"
        self.jobid_config = jobid_config

    @staticmethod
    def get_wandb_key(key_path):
        try:
            try:
                key_json = json.load(open(os.path.join(key_path, "key.json"), "r"))
                wandb_key = key_json["wandb_key"]
                return wandb_key
            except FileNotFoundError:
                print("Cannot use wandb module because key.json is not found under key_path")
                return ""
        except KeyError:
            print("Cannot use wandb module because wandb key is not specified")
            return ""

    def set_wandb_per_trial(self):
        print("before wandb.init\n\n\n")
        try:
            import wandb
            try:
                if os.environ["WANDB_MODE"] == "online":
                    os.environ["WANDB_SILENT"] = "false"
                    return wandb.init(project=self.jobid_config.get_jobid_full_data_name(),
                                      group=self.wandb_group_name,
                                      name=str(WandbUtils._get_next_trial_ids()),
                                      settings=wandb.Settings(
                                          _disable_stats=True),
                                      reinit=False)
                else:
                    return None
            except wandb.errors.UsageError as err:
                print(err)
                return None
        except ImportError:
            print("Cannot use wandb module because wandb is not installed, run pip install wandb==0.10.26")

    @staticmethod
    def _get_next_trial_ids():
        hash = hashlib.sha1()
        hash.update(str(time()).encode('utf-8'))
        return "trial_" + hash.hexdigest()[:3]

    def set_wandb_per_run(self):
        try:
            import wandb
            os.environ["WANDB_RUN_GROUP"] = self.jobid_config.to_wandb_string() + wandb.util.generate_id()
            self.wandb_group_name = os.environ["WANDB_RUN_GROUP"]
            try:
                if os.environ["WANDB_MODE"] == "online":
                    os.environ["WANDB_SILENT"] = "false"
                    return wandb.init(project=self.jobid_config.get_jobid_full_data_name(),
                                      group=os.environ["WANDB_RUN_GROUP"],
                                      settings=wandb.Settings(
                                          _disable_stats=True),
                                      reinit=False)
                else:
                    return None
            except wandb.errors.UsageError as err:
                print(err)
                return None
        except ImportError:
            print("Cannot use wandb module because wandb is not installed, run pip install wandb==0.10.26")
