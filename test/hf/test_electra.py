'''Require: pip install torch transformers datasets flaml[blendsearch,ray]
'''
import time
import numpy as np
import os

try:
    import ray
    from datasets import (
        load_dataset,
        load_metric,
    )
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        Trainer,
        TrainingArguments,
    )
    import flaml
    MODEL_CHECKPOINT = "google/electra-base-discriminator"
    task_to_keys = {
        "cola": ("sentence", None),
        "mnli": ("premise", "hypothesis"),
        "mrpc": ("sentence1", "sentence2"),
        "qnli": ("question", "sentence"),
        "qqp": ("question1", "question2"),
        "rte": ("sentence1", "sentence2"),
        "sst2": ("sentence", None),
        "stsb": ("sentence1", "sentence2"),
        "wnli": ("sentence1", "sentence2"),
    }
    max_seq_length = 128
    overwrite_cache = False
    pad_to_max_length = True
    padding = "max_length"

    TASK = "qnli"
    # HP_METRIC, MODE = "loss", "min"
    HP_METRIC, MODE = "accuracy", "max"

    sentence1_key, sentence2_key = task_to_keys[TASK]
    # Define tokenize method
    tokenizer = AutoTokenizer.from_pretrained(MODEL_CHECKPOINT, use_fast=True)

    def tokenize(examples):
        args = (
            (examples[sentence1_key],) if sentence2_key is None else (
                examples[sentence1_key], examples[sentence2_key])
        )
        return tokenizer(*args, padding=padding, max_length=max_seq_length,
                         truncation=True)

except ImportError:
    print("pip install torch transformers datasets flaml[blendsearch,ray]")

import logging
logger = logging.getLogger(__name__)
os.makedirs('logs', exist_ok=True)
logger.addHandler(logging.FileHandler('logs/tune_electra.log'))
logger.setLevel(logging.INFO)


def train_electra(config: dict):

    # Load dataset and apply tokenizer
    data_raw = load_dataset("glue", TASK)
    data_encoded = data_raw.map(tokenize, batched=True)
    train_dataset, eval_dataset = data_encoded["train"], data_encoded["validation"]

    NUM_LABELS = len(train_dataset.features["label"].names)

    metric = load_metric("glue", TASK)

    def compute_metrics(eval_pred):
        predictions, labels = eval_pred
        predictions = np.argmax(predictions, axis=1)
        return metric.compute(predictions=predictions, references=labels)

    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_CHECKPOINT, num_labels=NUM_LABELS
    )

    training_args = TrainingArguments(
        output_dir='.',
        do_eval=False,
        disable_tqdm=True,
        logging_steps=20000,
        save_total_limit=0,
        fp16=True,
        **config,
    )

    trainer = Trainer(
        model,
        training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        tokenizer=tokenizer,
        compute_metrics=compute_metrics,
    )

    # train model
    trainer.train()

    # evaluate model
    eval_output = trainer.evaluate()

    flaml.tune.report(
        loss=eval_output["eval_loss"],
        accuracy=eval_output["eval_accuracy"],
    )

    try:
        from azureml.core import Run
        run = Run.get_context()
        run.log('accuracy', eval_output["eval_accuracy"])
        run.log('loss', eval_output["eval_loss"])
        run.log('config', config)
    except ImportError:
        pass


def _test_electra(method='BlendSearch'):

    max_num_epoch = 9
    num_samples = -1
    time_budget_s = 3600

    search_space = {
        # You can mix constants with search space objects.
        "num_train_epochs": flaml.tune.loguniform(1, max_num_epoch),
        "learning_rate": flaml.tune.loguniform(3e-5, 1.5e-4),
        "weight_decay": flaml.tune.uniform(0, 0.3),
        "per_device_train_batch_size": flaml.tune.choice([16, 32, 64, 128]),
        "seed": flaml.tune.choice([12, 22, 33, 42]),
    }

    start_time = time.time()
    ray.init(num_cpus=4, num_gpus=4)
    if 'ASHA' == method:
        algo = None
    elif 'BOHB' == method:
        from ray.tune.schedulers import HyperBandForBOHB
        from ray.tune.suggest.bohb import tuneBOHB
        algo = tuneBOHB(max_concurrent=4)
        scheduler = HyperBandForBOHB(max_t=max_num_epoch)
    elif 'Optuna' == method:
        from ray.tune.suggest.optuna import OptunaSearch
        algo = OptunaSearch()
    elif 'CFO' == method:
        from flaml import CFO
        algo = CFO(low_cost_partial_config={
            "num_train_epochs": 1,
            "per_device_train_batch_size": 128,
        })
    elif 'BlendSearch' == method:
        from flaml import BlendSearch
        algo = BlendSearch(low_cost_partial_config={
            "num_train_epochs": 1,
            "per_device_train_batch_size": 128,
        })
    elif 'Dragonfly' == method:
        from ray.tune.suggest.dragonfly import DragonflySearch
        algo = DragonflySearch()
    elif 'SkOpt' == method:
        from ray.tune.suggest.skopt import SkOptSearch
        algo = SkOptSearch()
    elif 'Nevergrad' == method:
        from ray.tune.suggest.nevergrad import NevergradSearch
        import nevergrad as ng
        algo = NevergradSearch(optimizer=ng.optimizers.OnePlusOne)
    elif 'ZOOpt' == method:
        from ray.tune.suggest.zoopt import ZOOptSearch
        algo = ZOOptSearch(budget=num_samples)
    elif 'Ax' == method:
        from ray.tune.suggest.ax import AxSearch
        algo = AxSearch(max_concurrent=3)
    elif 'HyperOpt' == method:
        from ray.tune.suggest.hyperopt import HyperOptSearch
        algo = HyperOptSearch()
        scheduler = None
    if method != 'BOHB':
        from ray.tune.schedulers import ASHAScheduler
        scheduler = ASHAScheduler(
            max_t=max_num_epoch,
            grace_period=1)
    scheduler = None
    analysis = ray.tune.run(
        train_electra,
        metric=HP_METRIC,
        mode=MODE,
        resources_per_trial={"gpu": 4, "cpu": 4},
        config=search_space, local_dir='logs/',
        num_samples=num_samples, time_budget_s=time_budget_s,
        keep_checkpoints_num=1, checkpoint_score_attr=HP_METRIC,
        scheduler=scheduler, search_alg=algo)

    ray.shutdown()

    best_trial = analysis.get_best_trial(HP_METRIC, MODE, "all")
    metric = best_trial.metric_analysis[HP_METRIC][MODE]

    logger.info(f"method={method}")
    logger.info(f"n_trials={len(analysis.trials)}")
    logger.info(f"time={time.time()-start_time}")
    logger.info(f"Best model eval {HP_METRIC}: {metric:.4f}")
    logger.info(f"Best model parameters: {best_trial.config}")


def _test_electra_cfo():
    _test_electra('CFO')


def _test_electra_dragonfly():
    _test_electra('Dragonfly')


def _test_electra_skopt():
    _test_electra('SkOpt')


def _test_electra_nevergrad():
    _test_electra('Nevergrad')


def _test_electra_zoopt():
    _test_electra('ZOOpt')


def _test_electra_ax():
    _test_electra('Ax')


def __test_electra_hyperopt():
    _test_electra('HyperOpt')


def _test_electra_optuna():
    _test_electra('Optuna')


def _test_electra_asha():
    _test_electra('ASHA')


def _test_electra_bohb():
    _test_electra('BOHB')


if __name__ == "__main__":
    _test_electra()
