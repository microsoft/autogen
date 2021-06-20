import json
import os
import numpy as np
import time

try:
    import ray
    import transformers
    from transformers import TrainingArguments
    import datasets
    from .dataset.task_auto import get_default_task
    from .result_analysis.azure_utils import JobID
    from .huggingface.trainer import TrainerForAutoTransformers
except ImportError:
    print("To use the nlp component in flaml, run pip install flaml[nlp]")

task_list = [
    "seq-classification",
    "regression",
    "question-answering"
]


class AutoTransformers:
    '''The AutoTransformers class

    Example:

        .. code-block:: python

            autohf = AutoTransformers()
            autohf_settings = {"resources_per_trial": {"cpu": 1},
                       "num_samples": -1,
                       "time_budget": 100000,
                       "ckpt_per_epoch": 1,
                       "fp16": False,
                      }

            validation_metric, analysis = autohf.fit(**autohf_settings)

    '''

    @staticmethod
    def _convert_dict_to_ray_tune_space(config_json, mode="grid"):
        search_space = {}

        if mode == "grid":
            for each_hp in config_json.keys():
                this_config = config_json[each_hp]
                assert isinstance(this_config, dict) or isinstance(this_config, list), \
                    "config of " + each_hp + " must be dict or list"
                search_space[each_hp] = ray.tune.grid_search(this_config)
        else:
            for each_hp in config_json.keys():
                this_config = config_json[each_hp]
                assert isinstance(this_config, dict) or isinstance(this_config, list), \
                    "config of " + each_hp + " must be dict or list"
                if isinstance(this_config, dict):
                    lower = this_config["l"]
                    upper = this_config["u"]
                    space = this_config["space"]
                    if space == "log":
                        search_space[each_hp] = ray.tune.loguniform(lower, upper)
                    elif space == "linear":
                        search_space[each_hp] = ray.tune.uniform(lower, upper)
                    elif space == "quniform":
                        search_space[each_hp] = ray.tune.quniform(lower, upper, this_config["interval"])
                else:
                    search_space[each_hp] = ray.tune.choice(this_config)

        return search_space

    def _set_search_space(self,
                          **custom_hpo_args):
        from .hpo.hpo_searchspace import AutoHPOSearchSpace

        search_space_hpo_json \
            = AutoHPOSearchSpace.from_model_and_dataset_name(self.jobid_config.spa,
                                                             self.jobid_config.pre,
                                                             self.jobid_config.presz,
                                                             self.jobid_config.dat,
                                                             self.jobid_config.subdat,
                                                             **custom_hpo_args)
        self._search_space_hpo = AutoTransformers._convert_dict_to_ray_tune_space(
            search_space_hpo_json,
            mode=self.jobid_config.mod)

    @staticmethod
    def _wrapper(func, *args):  # with star
        return func(*args)

    @staticmethod
    def _get_split_name(data_raw, fold_name=None):
        if fold_name:
            return fold_name
        fold_keys = data_raw.keys()
        if fold_keys == {"train", "validation", "test"}:
            return "train", "validation", "test"
        for each_key in fold_keys:
            for each_split_name in {"train", "validation", "test"}:
                assert not (each_key.startswith(each_split_name) and each_key != each_split_name), \
                    "Dataset split must be within {}, must be explicitly specified in dataset_config, e.g.," \
                    "'fold_name': ['train','validation_matched','test_matched']. Please refer to the example in the " \
                    "documentation of AutoTransformers.prepare_data()".format(",".join(fold_keys))
        return "train", "validation", "test"

    def prepare_data(self,
                     data_root_path,
                     jobid_config=None,
                     is_wandb_on=False,
                     server_name=None,
                     max_seq_length=128,
                     fold_name=None,
                     resplit_portion=None,
                     **custom_data_args):
        """Prepare data

            Example:

                .. code-block:: python

                    preparedata_setting = {"server_name": "tmdev", "data_root_path": "data/", "max_seq_length": 128,
                                               "jobid_config": jobid_config, "wandb_utils": wandb_utils,
                                               "resplit_portion": {"source": ["train", "validation"],
                                               "train": [0, 0.8], "validation": [0.8, 0.9], "test": [0.9, 1.0]}}

                    autohf.prepare_data(**preparedata_setting)

            Args:
                server_name:
                    A string variable, which can be tmdev or azureml
                data_root_path:
                    The root path for storing the checkpoints and output results, e.g., "data/"
                jobid_config:
                    A JobID object describing the profile of job
                wandb_utils:
                    A WandbUtils object for wandb operations
                max_seq_length (optional):
                    Max_seq_lckpt_per_epochength for the huggingface, this hyperparameter must be specified
                    at the data processing step
                resplit_portion:
                    The proportion for resplitting the train and dev data when split_mode="resplit".
                    If args.resplit_mode = "rspt", resplit_portion is required
                is_wandb_on:
                    A boolean variable indicating whether wandb is used
        """
        from .dataset.dataprocess_auto import AutoEncodeText
        from transformers import AutoTokenizer
        from datasets import load_dataset
        from .utils import PathUtils
        from .utils import load_dft_args

        self._max_seq_length = max_seq_length
        self._server_name = server_name if server_name is not None else "tmdev"
        """
            loading the jobid config from console args
        """
        console_args = load_dft_args()
        self.jobid_config = JobID(console_args)
        if jobid_config:
            self.jobid_config = jobid_config
        if len(custom_data_args) > 0:
            self.jobid_config.set_jobid_from_console_args(console_args=custom_data_args)
        if is_wandb_on:
            from .result_analysis.wandb_utils import WandbUtils
            self.wandb_utils = WandbUtils(is_wandb_on=is_wandb_on,
                                          wandb_key_path=console_args.key_path,
                                          jobid_config=self.jobid_config)
            self.wandb_utils.set_wandb_per_run()
        else:
            self.wandb_utils = None

        self.path_utils = PathUtils(self.jobid_config, hpo_data_root_path=data_root_path)

        if self.jobid_config.spt == "rspt":
            assert resplit_portion, "If split mode is 'rspt', the resplit_portion must be provided. Please " \
                                    "refer to the example in the documentation of AutoTransformers.prepare_data()"
        if self.jobid_config.subdat:
            data_raw = load_dataset(JobID.dataset_list_to_str(self.jobid_config.dat),
                                    self.jobid_config.subdat)
        else:
            data_raw = AutoTransformers._wrapper(load_dataset, *self.jobid_config.dat)

        self._train_name, self._dev_name, self._test_name = AutoTransformers._get_split_name(
            data_raw,
            fold_name=fold_name)
        auto_tokentoids_config = {"max_seq_length": self._max_seq_length}
        self._tokenizer = AutoTokenizer.from_pretrained(self.jobid_config.pre_full, use_fast=True)

        def autoencodetext_from_model_and_dataset_name():
            return AutoEncodeText.from_model_and_dataset_name(
                data_raw,
                self.jobid_config.pre_full,
                self.jobid_config.dat,
                self.jobid_config.subdat,
                **auto_tokentoids_config)

        data_encoded = autoencodetext_from_model_and_dataset_name()
        self._max_seq_length = 0
        """
            Update the max_seq_length to the minimum of the actual max seq length and the user defined max_seq_length
        """
        for each_fold in data_encoded.keys():
            self._max_seq_length = max(self._max_seq_length,
                                       max([sum(data_encoded[each_fold][x]['attention_mask']) for x in
                                            range(len(data_encoded[each_fold]))]))
        self._max_seq_length = int((self._max_seq_length + 15) / 16) * 16
        data_encoded = autoencodetext_from_model_and_dataset_name()

        if self.jobid_config.spt == "rspt":
            all_folds_from_source = []
            assert "source" in resplit_portion.keys(), "Must specify the source for resplitting the dataset in" \
                                                       "resplit_portion, which is a list of folder names, e.g., " \
                                                       "resplit_portion = {'source': ['train']}"

            source_fold_names = resplit_portion['source']
            for each_fold_name in source_fold_names:
                this_fold_dataset = data_encoded[each_fold_name]
                all_folds_from_source.append(this_fold_dataset)

            merged_folds_from_source = datasets.concatenate_datasets(all_folds_from_source)
            merged_folds_from_source = merged_folds_from_source.shuffle(seed=self.jobid_config.sddt)

            assert "train" in resplit_portion.keys() and "validation" in resplit_portion.keys() \
                   and "test" in resplit_portion.keys(), "train, validation, test must exist in resplit_portion"

            for key in ["train", "validation", "test"]:
                target_fold_start, target_fold_end = \
                    int(resplit_portion[key][0] * len(merged_folds_from_source)), \
                    int(resplit_portion[key][1] * len(merged_folds_from_source))
                subfold_dataset = merged_folds_from_source.select(
                    [x for x in range(target_fold_start, target_fold_end)]).flatten_indices()
                if key == "train":
                    self.train_dataset = subfold_dataset
                elif key == "validation":
                    self.eval_dataset = subfold_dataset
                else:
                    self.test_dataset = subfold_dataset
        else:
            self.train_dataset, self.eval_dataset, self.test_dataset \
                = data_encoded[self._train_name], data_encoded[self._dev_name], data_encoded[self._test_name]

    def _load_model(self,
                    checkpoint_path=None,
                    per_model_config=None):
        from transformers import AutoConfig
        from .huggingface.switch_head_auto import AutoSeqClassificationHead, MODEL_CLASSIFICATION_HEAD_MAPPING

        this_task = get_default_task(self.jobid_config.dat,
                                     self.jobid_config.subdat)
        if this_task == "seq-classification":
            self._num_labels = len(self.train_dataset.features["label"].names)
        elif this_task == "regression":
            self._num_labels = 1

        if not checkpoint_path:
            checkpoint_path = self.jobid_config.pre_full

        def get_this_model():
            from transformers import AutoModelForSequenceClassification
            return AutoModelForSequenceClassification.from_pretrained(checkpoint_path, config=model_config)

        def is_pretrained_model_in_classification_head_list():
            return self.jobid_config.pre in MODEL_CLASSIFICATION_HEAD_MAPPING.keys()

        def _set_model_config():
            if per_model_config and len(per_model_config) > 0:
                model_config = AutoConfig.from_pretrained(
                    checkpoint_path,
                    num_labels=model_config_num_labels,
                    **per_model_config)
            else:
                model_config = AutoConfig.from_pretrained(
                    checkpoint_path,
                    num_labels=model_config_num_labels)
            return model_config

        if this_task == "seq-classification":
            num_labels_old = AutoConfig.from_pretrained(checkpoint_path).num_labels
            if is_pretrained_model_in_classification_head_list():
                model_config_num_labels = num_labels_old
            else:
                model_config_num_labels = self._num_labels
            model_config = _set_model_config()

            if is_pretrained_model_in_classification_head_list():
                if self._num_labels != num_labels_old:
                    this_model = get_this_model()
                    model_config.num_labels = self._num_labels
                    this_model.num_labels = self._num_labels
                    this_model.classifier = AutoSeqClassificationHead \
                        .from_model_type_and_config(self.jobid_config.pre,
                                                    model_config)
                else:
                    this_model = get_this_model()
            else:
                this_model = get_this_model()

            this_model.resize_token_embeddings(len(self._tokenizer))
            return this_model
        elif this_task == "regression":
            model_config_num_labels = 1
            model_config = _set_model_config()
            this_model = get_this_model()
            return this_model

    def _get_metric_func(self):
        data_name = JobID.dataset_list_to_str(self.jobid_config.dat)
        if data_name in ("glue", "super_glue"):
            metric = datasets.load.load_metric(data_name, self.jobid_config.subdat)
        elif data_name in ("squad", "squad_v2"):
            metric = datasets.load.load_metric(data_name)
        else:
            metric = datasets.load.load_metric(self.metric_name)
        return metric

    def _compute_metrics_by_dataset_name(self,
                                         eval_pred):
        predictions, labels = eval_pred
        predictions = np.squeeze(predictions) \
            if self.task_name == "regression" else np.argmax(predictions, axis=1)
        metric_func = self._get_metric_func()
        return metric_func.compute(predictions=predictions, references=labels)

    def _compute_checkpoint_freq(self,
                                 num_train_epochs,
                                 batch_size):
        if "gpu" in self._resources_per_trial:
            ckpt_step_freq = int(min(num_train_epochs, 1) * len(self.train_dataset) / batch_size
                                 / self._resources_per_trial["gpu"] / self.ckpt_per_epoch) + 1
        else:
            ckpt_step_freq = int(min(num_train_epochs, 1) * len(self.train_dataset) / batch_size
                                 / self._resources_per_trial["cpu"] / self.ckpt_per_epoch) + 1

        return ckpt_step_freq

    @staticmethod
    def _separate_config(config):

        training_args_config = {}
        per_model_config = {}

        for key in config.keys():
            if key in TrainingArguments.__dict__.keys():
                training_args_config[key] = config[key]
            else:
                per_model_config[key] = config[key]

        return training_args_config, per_model_config

    def _objective(self, config, reporter, checkpoint_dir=None):
        from transformers.trainer_utils import set_seed
        self._set_transformers_verbosity(self._transformers_verbose)

        def model_init():
            return self._load_model()
        set_seed(config["seed"])

        training_args_config, per_model_config = AutoTransformers._separate_config(config)
        this_model = self._load_model(per_model_config=per_model_config)

        trial_id = reporter.trial_id
        self.path_utils.make_dir_per_trial(trial_id)

        ckpt_freq = self._compute_checkpoint_freq(
            num_train_epochs=config["num_train_epochs"],
            batch_size=config["per_device_train_batch_size"])

        assert self.path_utils.ckpt_dir_per_trial

        if transformers.__version__.startswith("3"):
            training_args = TrainingArguments(
                output_dir=self.path_utils.ckpt_dir_per_trial,
                do_eval=True,
                per_device_eval_batch_size=32,
                eval_steps=ckpt_freq,
                evaluate_during_training=True,
                save_steps=ckpt_freq,
                save_total_limit=0,
                fp16=self._fp16,
                **training_args_config,
            )
        else:
            from transformers import IntervalStrategy
            training_args = TrainingArguments(
                output_dir=self.path_utils.ckpt_dir_per_trial,
                do_eval=True,
                per_device_eval_batch_size=32,
                eval_steps=ckpt_freq,
                evaluation_strategy=IntervalStrategy.STEPS,
                save_steps=ckpt_freq,
                save_total_limit=0,
                fp16=self._fp16,
                **training_args_config,
            )

        trainer = TrainerForAutoTransformers(
            model=this_model,
            args=training_args,
            model_init=model_init,
            train_dataset=self.train_dataset,
            eval_dataset=self.eval_dataset,
            tokenizer=self._tokenizer,
            compute_metrics=self._compute_metrics_by_dataset_name,
        )
        trainer.trial_id = reporter.trial_id

        """
            create a wandb run. If os.environ["WANDB_MODE"] == "offline", run = None
        """

        if self.wandb_utils:
            run = self.wandb_utils.set_wandb_per_trial()
            import wandb
            for each_hp in config:
                wandb.log({each_hp: config[each_hp]})
        else:
            run = None

        trainer.train()
        trainer.evaluate(self.eval_dataset)
        """
            If a wandb run was created, close the run after train and evaluate finish
        """
        if run:
            run.finish()

    def _verify_init_config(self,
                            **custom_hpo_args):
        for key in custom_hpo_args.keys():
            if key == "points_to_evaluate":
                for each_init_config in custom_hpo_args[key]:
                    for each_hp in each_init_config.keys():
                        assert each_hp in self._search_space_hpo.keys(), \
                            "points_to_evaluate hp must be within the search space"

                        assert isinstance(each_init_config[each_hp], int) or \
                               isinstance(each_init_config[each_hp], float) or \
                               isinstance(each_init_config[each_hp], str) or \
                               isinstance(each_init_config[each_hp], bool), " points_to_evaluate must be a scalar"

                        assert isinstance(self._search_space_hpo[each_hp], ray.tune.sample.Categorical) or \
                               isinstance(self._search_space_hpo[each_hp], ray.tune.sample.Float) or \
                               isinstance(self._search_space_hpo[each_hp], ray.tune.sample.Integer), \
                               "Every hp space must either be categorical, integer or float"

                        if isinstance(self._search_space_hpo[each_hp], ray.tune.sample.Categorical):
                            assert each_init_config[each_hp] in self._search_space_hpo[each_hp].categories, \
                                "points_to_evaluate {each_hp} value must be within the search space"
                        else:
                            assert self._search_space_hpo[each_hp].lower <= each_init_config[each_hp] <= \
                                   self._search_space_hpo[each_hp].upper, \
                                   "points_to_evaluate {each_hp} value must be within the search space"

    def _get_search_algo(self,
                         search_algo_name,
                         search_algo_args_mode,
                         **custom_hpo_args):
        from .hpo.searchalgo_auto import AutoSearchAlgorithm

        if search_algo_name in ("bs", "cfo"):
            self._verify_init_config(**custom_hpo_args)
        search_algo = AutoSearchAlgorithm.from_method_name(
            search_algo_name,
            search_algo_args_mode,
            self._search_space_hpo,
            **custom_hpo_args)
        return search_algo

    @staticmethod
    def _recover_checkpoint(tune_checkpoint_dir):
        assert tune_checkpoint_dir
        # Get subdirectory used for Huggingface.
        subdirs = [
            os.path.join(tune_checkpoint_dir, name)
            for name in os.listdir(tune_checkpoint_dir)
            if os.path.isdir(os.path.join(tune_checkpoint_dir, name))
        ]
        # There should only be 1 subdir.
        assert len(subdirs) == 1, subdirs
        return subdirs[0]

    def _save_ckpt_json(self,
                        best_ckpt):
        json.dump({"best_ckpt": best_ckpt},
                  open(os.path.join(self.path_utils.result_dir_per_run,
                                    "save_ckpt_" + self.jobid_config.to_jobid_string() + ".json"), "w"))

    def _save_output_metric(self,
                            output_metrics):
        json.dump(output_metrics, open(
            os.path.join(self.path_utils.result_dir_per_run,
                         "output_metric_" + self.jobid_config.to_jobid_string() + ".json"), "w"))

    def _load_ckpt_json(self,
                        ckpt_dir=None,
                        **kwargs):
        if not ckpt_dir:
            ckpt_dir = os.path.join(self.path_utils.result_dir_per_run,
                                    "save_ckpt_" + self.jobid_config.to_jobid_string() + ".json")
        try:
            ckpt_json = json.load(open(ckpt_dir))
            return ckpt_json["best_ckpt"]
        except FileNotFoundError as err:
            print("Saved checkpoint not found. Please make sure checkpoint is stored under {}".format(ckpt_dir))
            raise err

    def _set_metric(self, custom_metric_name=None, custom_metric_mode_name=None):
        from .dataset.metric_auto import get_default_and_alternative_metric
        from .utils import _variable_override_default_alternative

        default_metric, default_mode, all_metrics, all_modes = \
            get_default_and_alternative_metric(
                dataset_name_list=self.jobid_config.dat,
                subdataset_name=self.jobid_config.subdat,
                custom_metric_name=custom_metric_name,
                custom_metric_mode_name=custom_metric_mode_name)
        _variable_override_default_alternative(self,
                                               "metric_name",
                                               default_metric,
                                               all_metrics,
                                               custom_metric_name)
        _variable_override_default_alternative(self,
                                               "metric_mode_name",
                                               default_mode,
                                               all_modes,
                                               custom_metric_mode_name)
        self._all_metrics = all_metrics
        self._all_modes = all_modes

    def _set_task(self):
        self.task_name = get_default_task(self.jobid_config.dat,
                                          self.jobid_config.subdat)

    def fit_hf(self,
               resources_per_trial,
               num_samples,
               time_budget,
               custom_metric_name=None,
               custom_metric_mode_name=None,
               _fp16=True,
               **custom_hpo_args
               ):
        from transformers.trainer_utils import HPSearchBackend

        '''Fine tuning the huggingface using HF's API Transformers.hyperparameter_search (for comparitive purpose).
               Transformers.hyperparameter_search has the following disadvantages:
            (1) it does not return tune.analysis.Analysis result, what is analysis used for
            (2) it is inconvenient to develop on top of Transformers.hyperparameter_search, whose trainable function,
                 search space, etc. are defined inside of Transformers.hyperparameter_search.
               An example:
            autohf_settings = {"resources_per_trial": {"cpu": 1},
                       "num_samples": 1,
                       "time_budget": 100000,
                       "ckpt_per_epoch": 1,
                       "fp16": False,
                      }
            validation_metric, analysis = autohf.fit(**autohf_settings,)
            Args:
                resources_per_trial:
                    A dict showing the resources used by each trial,
                    e.g., {"gpu": 4, "cpu": 4}
                num_samples:
                    An int variable of the maximum number of trials
                time_budget:
                    An int variable of the maximum time budget
                custom_metric_name:
                    A string of the dataset name or a function,
                    e.g., 'accuracy', 'f1', 'loss',
                custom_metric_mode_name:
                    A string of the mode name,
                    e.g., "max", "min", "last", "all"
                fp16:
                    boolean, default = True | whether to use fp16
                custom_hpo_args:
                    The additional keyword arguments, e.g.,
                    custom_hpo_args = {"points_to_evaluate": [{
                               "num_train_epochs": 1,
                               "per_device_train_batch_size": 128, }]}
            Returns:
               validation_metric:
                    a dict storing the validation score
            '''

        def model_init():
            return self._load_model()

        def ray_hp_space(trial):
            return {
                "learning_rate": ray.tune.loguniform(1e-6, 1e-4),
                "num_train_epochs": ray.tune.choice(list(range(1, 6))),
                "seed": ray.tune.quniform(1, 41, 1),
                "per_device_train_batch_size": ray.tune.choice([4, 8, 16, 32, 64]),
            }

        self._set_metric(custom_metric_name, custom_metric_mode_name)
        self._set_task()

        training_args = TrainingArguments(
            output_dir=self.path_utils.hpo_ckpt_path,
            fp16=_fp16,
        )
        this_model = self._load_model()

        trainer = TrainerForAutoTransformers(
            this_model,
            training_args,
            model_init=model_init,
            train_dataset=self.train_dataset,
            eval_dataset=self.eval_dataset,
            tokenizer=self._tokenizer,
            compute_metrics=self._compute_metrics_by_dataset_name,
        )
        self.path_utils.make_dir_per_run()

        start_time = time.time()
        best_run = trainer.hyperparameter_search(
            n_trials=num_samples,
            time_budget_s=time_budget,
            # hp_space=ray_hp_space,
            backend=HPSearchBackend.RAY,
            resources_per_trial=resources_per_trial)
        duration = time.time() - start_time
        self.last_run_duration = duration
        print("Total running time: {} seconds".format(duration))

        hp_dict = best_run.hyperparameters
        hp_dict["seed"] = int(hp_dict["seed"])

        best_training_args = TrainingArguments(
            output_dir=self.path_utils.hpo_ckpt_path,
            fp16=_fp16,
            **hp_dict,
        )

        best_trainer = TrainerForAutoTransformers(
            this_model,
            best_training_args,
            model_init=model_init,
            train_dataset=self.train_dataset,
            eval_dataset=self.eval_dataset,
            tokenizer=self._tokenizer,
            compute_metrics=self._compute_metrics_by_dataset_name,
        )

        best_model_checkpoint_path = os.path.join(self.path_utils.hpo_ckpt_path, "hpo_hf")
        if not os.path.exists(best_model_checkpoint_path):
            os.mkdir(best_model_checkpoint_path)
        best_trainer.train()
        best_trainer.save_model(best_model_checkpoint_path)
        self._save_ckpt_json(best_model_checkpoint_path)
        validation_metric = best_trainer.evaluate()

        return validation_metric

    def _set_transformers_verbosity(self, transformers_verbose):
        if transformers_verbose == transformers.logging.ERROR:
            transformers.logging.set_verbosity_error()
        elif transformers_verbose == transformers.logging.WARNING:
            transformers.logging.set_verbosity_warning()
        elif transformers_verbose == transformers.logging.INFO:
            transformers.logging.set_verbosity_info()
        elif transformers_verbose == transformers.logging.DEBUG:
            transformers.logging.set_verbosity_debug()
        else:
            raise Exception("transformers_verbose must be set to ERROR, WARNING, INFO or DEBUG")

    def fit(self,
            num_samples,
            time_budget,
            custom_metric_name=None,
            custom_metric_mode_name=None,
            ckpt_per_epoch=1,
            fp16=True,
            ray_verbose=1,
            transformers_verbose=10,
            resources_per_trial=None,
            ray_local_mode=False,
            **custom_hpo_args):
        """Fine tuning the huggingface using the hpo setting

        Example:

            .. code-block:: python

                autohf_settings = {"resources_per_trial": {"cpu": 1},
                           "num_samples": 1,
                           "time_budget": 100000,
                           "ckpt_per_epoch": 1,
                           "fp16": False,
                          }

                validation_metric, analysis = autohf.fit(**autohf_settings)

        Args:
            resources_per_trial:
                A dict showing the resources used by each trial,
                e.g., {"gpu": 4, "cpu": 4}
            num_samples:
                An int variable of the maximum number of trials
            time_budget:
                An int variable of the maximum time budget
            custom_metric_name:
                A string of the dataset name or a function,
                e.g., 'accuracy', 'f1', 'loss'
            custom_metric_mode_name:
                A string of the mode name,
                e.g., "max", "min", "last", "all"
            ckpt_per_epoch:
                An integer value of number of checkpoints per epoch, default = 1
            ray_verbose:
                An integer, default=1 | verbosit of ray,
            transformers_verbose:
                An integer, default=transformers.logging.INFO | verbosity of transformers, must be chosen from one of
                transformers.logging.ERROR, transformers.logging.INFO, transformers.logging.WARNING,
                or transformers.logging.DEBUG
            fp16:
                A boolean, default = True | whether to use fp16
            ray_local_mode:
                A boolean, default = False | whether to use the local mode (debugging mode) for ray tune.run
            custom_hpo_args:
                The additional keyword arguments, e.g., custom_hpo_args = {"points_to_evaluate": [{
                "num_train_epochs": 1, "per_device_train_batch_size": 128, }]}

        Returns:

            validation_metric: A dict storing the validation score

            analysis: A ray.tune.analysis.Analysis object storing the analysis results from tune.run
        """
        from .hpo.scheduler_auto import AutoScheduler
        self._transformers_verbose = transformers_verbose

        """
         Specify the other parse of jobid configs from custom_hpo_args, e.g., if the search algorithm was not specified
         previously, can specify the algorithm here
        """
        if len(custom_hpo_args) > 0:
            self.jobid_config.set_jobid_from_console_args(console_args=custom_hpo_args)

        self._resources_per_trial = resources_per_trial
        self._set_metric(custom_metric_name, custom_metric_mode_name)
        self._set_task()
        self._fp16 = fp16
        ray.init(local_mode=ray_local_mode)
        self._set_search_space(**custom_hpo_args)

        search_algo = self._get_search_algo(self.jobid_config.alg, self.jobid_config.arg, **custom_hpo_args)
        scheduler = AutoScheduler.from_scheduler_name(self.jobid_config.pru)
        self.ckpt_per_epoch = ckpt_per_epoch
        self.path_utils.make_dir_per_run()

        assert self.path_utils.ckpt_dir_per_run
        start_time = time.time()

        tune_config = self._search_space_hpo
        tune_config["seed"] = self.jobid_config.sdhf

        analysis = ray.tune.run(
            self._objective,
            metric=self.metric_name,
            mode=self.metric_mode_name,
            name="ray_result",
            resources_per_trial=resources_per_trial,
            config=tune_config,
            verbose=ray_verbose,
            local_dir=self.path_utils.ckpt_dir_per_run,
            num_samples=num_samples,
            time_budget_s=time_budget,
            keep_checkpoints_num=1,
            scheduler=scheduler,
            search_alg=search_algo,
        )
        duration = time.time() - start_time
        self.last_run_duration = duration
        print("Total running time: {} seconds".format(duration))

        ray.shutdown()

        best_trial = analysis.get_best_trial(scope="all", metric=self.metric_name, mode=self.metric_mode_name)
        validation_metric = {"eval_" + self.metric_name
                             : best_trial.metric_analysis[self.metric_name][self.metric_mode_name]}
        for x in range(len(self._all_metrics)):
            validation_metric["eval_" + self._all_metrics[x]] \
                = best_trial.metric_analysis[self._all_metrics[x]][self._all_modes[x]]

        get_best_ckpt = analysis.get_best_checkpoint(best_trial, metric=self.metric_name, mode=self.metric_mode_name)
        best_ckpt = AutoTransformers._recover_checkpoint(get_best_ckpt)

        self._save_ckpt_json(best_ckpt)

        return validation_metric, analysis

    def predict(self,
                ckpt_json_dir=None,
                **kwargs):
        '''Predict label for test data.

        An example:
            predictions, test_metric = autohf.predict()

        Args:
            ckpt_json_dir:
                the checkpoint for the fine-tuned huggingface if you wish to override
                the saved checkpoint in the training stage under self.path_utils._result_dir_per_run

        Returns:
            A numpy array of shape n * 1 - - each element is a predicted class
            label for an instance.
        '''
        best_checkpoint = self._load_ckpt_json(ckpt_json_dir, **kwargs)
        best_model = self._load_model(checkpoint_path=best_checkpoint)
        training_args = TrainingArguments(per_device_eval_batch_size=1,
                                          output_dir=self.path_utils.result_dir_per_run)
        test_trainer = TrainerForAutoTransformers(best_model, training_args)

        if self.jobid_config.spt == "ori":
            if "label" in self.test_dataset.features.keys():
                self.test_dataset.remove_columns_("label")
                print("Cleaning the existing label column from test data")

        test_dataloader = test_trainer.get_test_dataloader(self.test_dataset)
        predictions, labels, _ = test_trainer.prediction_loop(test_dataloader, description="Prediction")
        predictions = np.squeeze(predictions) \
            if get_default_task(self.jobid_config.dat,
                                self.jobid_config.subdat) == "regression" \
            else np.argmax(predictions, axis=1)

        if self.jobid_config.spt == "rspt":
            assert labels is not None
            metric = self._get_metric_func()
            output_metric = metric.compute(predictions=predictions, references=labels)
            self._save_output_metric(output_metric)
            return predictions, output_metric
        else:
            return predictions, None

    def output_prediction(self,
                          predictions=None,
                          output_prediction_path=None,
                          output_zip_file_name=None):
        """
            When using the original GLUE split, output the prediction on test data,
            and prepare the .zip file for submission

            Example:
                local_archive_path = self.autohf.output_prediction(predictions,
                                      output_prediction_path= self.console_args.data_root_dir + "result/",
                                      output_zip_file_name=azure_save_file_name)

            Args:
                predictions:
                    A list of predictions, which is the output of AutoTransformers.predict()
                output_prediction_path:
                    Output path for the prediction
                output_zip_file_name:
                    An string, which is the name of the output zip file

            Returns:
                The path of the output .zip file
        """
        from .dataset.submission_auto import auto_output_prediction
        return auto_output_prediction(self.jobid_config.dat,
                                      output_prediction_path,
                                      output_zip_file_name,
                                      predictions,
                                      self.train_dataset,
                                      self._dev_name,
                                      self.jobid_config.subdat)
