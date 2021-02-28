'''Require: pip install torch transformers datasets flaml[blendsearch,ray]
'''
import time
import numpy as np

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
    MODEL_CHECKPOINT = "distilbert-base-uncased"
    TASK = "cola"
    NUM_LABELS = 2
    COLUMN_NAME = "sentence"
    METRIC_NAME = "matthews_correlation"

    # HP_METRIC, MODE = "loss", "min"
    HP_METRIC, MODE = "matthews_correlation", "max"

    # Define tokenize method
    tokenizer = AutoTokenizer.from_pretrained(MODEL_CHECKPOINT, use_fast=True)
except:
    print("pip install torch transformers datasets flaml[blendsearch,ray]")
    
import logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.FileHandler('test/tune_distilbert.log'))
logger.setLevel(logging.INFO)

import flaml

def train_distilbert(config: dict):

    metric = load_metric("glue", TASK)

    def tokenize(examples):
        return tokenizer(examples[COLUMN_NAME], truncation=True)

    def compute_metrics(eval_pred):
        predictions, labels = eval_pred
        predictions = np.argmax(predictions, axis=1)
        return metric.compute(predictions=predictions, references=labels)

    # Load CoLA dataset and apply tokenizer
    cola_raw = load_dataset("glue", TASK)

    cola_encoded = cola_raw.map(tokenize, batched=True)
    train_dataset, eval_dataset = cola_encoded["train"], cola_encoded["validation"]

    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_CHECKPOINT, num_labels=NUM_LABELS
    )

    training_args = TrainingArguments(
        output_dir='.',
        do_eval=False,
        disable_tqdm=True,
        logging_steps=20000,
        save_total_limit=0,
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
        matthews_correlation=eval_output["eval_matthews_correlation"],
        )


def _test_distillbert(method='BlendSearch'):
 
    max_num_epoch = 64
    num_samples = -1
    time_budget_s = 3600

    search_space = {
        # You can mix constants with search space objects.
        "num_train_epochs": flaml.tune.loguniform(1, max_num_epoch),
        "learning_rate": flaml.tune.loguniform(1e-6, 1e-4),
        "adam_beta1": flaml.tune.uniform(0.8, 0.99),
        "adam_beta2": flaml.tune.loguniform(98e-2, 9999e-4),
        "adam_epsilon": flaml.tune.loguniform(1e-9, 1e-7),
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
        algo = CFO(points_to_evaluate=[{
            "num_train_epochs": 1,
        }])
    elif 'BlendSearch' == method:
        from flaml import BlendSearch
        algo = BlendSearch(points_to_evaluate=[{
            "num_train_epochs": 1,
        }])
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
        train_distilbert,
        metric=HP_METRIC,
        mode=MODE,
        resources_per_trial={"gpu": 4, "cpu": 4},
        config=search_space, local_dir='test/logs/',
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


def _test_distillbert_cfo():
    _test_distillbert('CFO')


def _test_distillbert_dragonfly():
    _test_distillbert('Dragonfly')


def _test_distillbert_skopt():
    _test_distillbert('SkOpt')


def _test_distillbert_nevergrad():
    _test_distillbert('Nevergrad')


def _test_distillbert_zoopt():
    _test_distillbert('ZOOpt')


def _test_distillbert_ax():
    _test_distillbert('Ax')


def __test_distillbert_hyperopt():
    _test_distillbert('HyperOpt')


def _test_distillbert_optuna():
    _test_distillbert('Optuna')


def _test_distillbert_asha():
    _test_distillbert('ASHA')


def _test_distillbert_bohb():
    _test_distillbert('BOHB')


if __name__ == "__main__":
    _test_distillbert()