# Tune - HuggingFace

This example uses flaml to finetune a transformer model from Huggingface transformers library.

*Note*: `flaml.AutoML` has built-in support for certain finetuning tasks with a
[higher-level API](AutoML-NLP).
It may be easier to use that API unless you have special requirements not handled by that API.

### Requirements

This example requires GPU. Install dependencies:
```python
pip install torch transformers datasets "flaml[blendsearch,ray]"
```

### Prepare for tuning

#### Tokenizer

```python
from transformers import AutoTokenizer

MODEL_NAME = "distilbert-base-uncased"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, use_fast=True)
COLUMN_NAME = "sentence"

def tokenize(examples):
    return tokenizer(examples[COLUMN_NAME], truncation=True)
```

#### Define training method

```python
import flaml
import datasets
from transformers import AutoModelForSequenceClassification

TASK = "cola"
NUM_LABELS = 2

def train_distilbert(config: dict):
    # Load CoLA dataset and apply tokenizer
    cola_raw = datasets.load_dataset("glue", TASK)
    cola_encoded = cola_raw.map(tokenize, batched=True)
    train_dataset, eval_dataset = cola_encoded["train"], cola_encoded["validation"]

    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, num_labels=NUM_LABELS
    )
    metric = datasets.load_metric("glue", TASK)

    def compute_metrics(eval_pred):
        predictions, labels = eval_pred
        predictions = np.argmax(predictions, axis=1)
        return metric.compute(predictions=predictions, references=labels)

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

    # report the metric to optimize & the metric to log
    flaml.tune.report(
        loss=eval_output["eval_loss"],
        matthews_correlation=eval_output["eval_matthews_correlation"],
    )
```

### Define the search

We are now ready to define our search. This includes:

- The `search_space` for our hyperparameters
- The `metric` and the `mode` ('max' or 'min') for optimization
- The constraints (`n_cpus`, `n_gpus`, `num_samples`, and `time_budget_s`)

```python
max_num_epoch = 64
search_space = {
        # You can mix constants with search space objects.
        "num_train_epochs": flaml.tune.loguniform(1, max_num_epoch),
        "learning_rate": flaml.tune.loguniform(1e-6, 1e-4),
        "adam_epsilon": flaml.tune.loguniform(1e-9, 1e-7),
        "adam_beta1": flaml.tune.uniform(0.8, 0.99),
        "adam_beta2": flaml.tune.loguniform(98e-2, 9999e-4),
}

# optimization objective
HP_METRIC, MODE = "matthews_correlation", "max"

# resources
num_cpus = 4
num_gpus = 4  # change according to your GPU resources

# constraints
num_samples = -1  # number of trials, -1 means unlimited
time_budget_s = 3600  # time budget in seconds
```

### Launch the tuning

We are now ready to launch the tuning using `flaml.tune.run`:

```python
import ray

ray.init(num_cpus=num_cpus, num_gpus=num_gpus)
print("Tuning started...")
analysis = flaml.tune.run(
    train_distilbert,
    search_alg=flaml.CFO(
        space=search_space,
        metric=HP_METRIC,
        mode=MODE,
        low_cost_partial_config={"num_train_epochs": 1}),
    resources_per_trial={"gpu": num_gpus, "cpu": num_cpus},
    local_dir='logs/',
    num_samples=num_samples,
    time_budget_s=time_budget_s,
    use_ray=True,
)
```

This will run tuning for one hour. At the end we will see a summary.
```
== Status ==
Memory usage on this node: 32.0/251.6 GiB
Using FIFO scheduling algorithm.
Resources requested: 0/4 CPUs, 0/4 GPUs, 0.0/150.39 GiB heap, 0.0/47.22 GiB objects (0/1.0 accelerator_type:V100)
Result logdir: /home/chiw/FLAML/notebook/logs/train_distilbert_2021-05-07_02-35-58
Number of trials: 22/infinite (22 TERMINATED)
Trial name	status	loc	adam_beta1	adam_beta2	adam_epsilon	learning_rate	num_train_epochs	iter	total time (s)	loss	matthews_correlation
train_distilbert_a0c303d0	TERMINATED		0.939079	0.991865	7.96945e-08	5.61152e-06	1	1	55.6909	0.587986	0
train_distilbert_a0c303d1	TERMINATED		0.811036	0.997214	2.05111e-09	2.05134e-06	1.44427	1	71.7663	0.603018	0
train_distilbert_c39b2ef0	TERMINATED		0.909395	0.993715	1e-07	5.26543e-06	1	1	53.7619	0.586518	0
train_distilbert_f00776e2	TERMINATED		0.968763	0.990019	4.38943e-08	5.98035e-06	1.02723	1	56.8382	0.581313	0
train_distilbert_11ab3900	TERMINATED		0.962198	0.991838	7.09296e-08	5.06608e-06	1	1	54.0231	0.585576	0
train_distilbert_353025b6	TERMINATED		0.91596	0.991892	8.95426e-08	6.21568e-06	2.15443	1	98.3233	0.531632	0.388893
train_distilbert_5728a1de	TERMINATED		0.926933	0.993146	1e-07	1.00902e-05	1	1	55.3726	0.538505	0.280558
train_distilbert_9394c2e2	TERMINATED		0.928106	0.990614	4.49975e-08	3.45674e-06	2.72935	1	121.388	0.539177	0.327295
train_distilbert_b6543fec	TERMINATED		0.876896	0.992098	1e-07	7.01176e-06	1.59538	1	76.0244	0.527516	0.379177
train_distilbert_0071f998	TERMINATED		0.955024	0.991687	7.39776e-08	5.50998e-06	2.90939	1	126.871	0.516225	0.417157
train_distilbert_2f830be6	TERMINATED		0.886931	0.989628	7.6127e-08	4.37646e-06	1.53338	1	73.8934	0.551629	0.0655887
train_distilbert_7ce03f12	TERMINATED		0.984053	0.993956	8.70144e-08	7.82557e-06	4.08775	1	174.027	0.523732	0.453549
train_distilbert_aaab0508	TERMINATED		0.940707	0.993946	1e-07	8.91979e-06	3.40243	1	146.249	0.511288	0.45085
train_distilbert_14262454	TERMINATED		0.99	0.991696	4.60093e-08	4.83405e-06	3.4954	1	152.008	0.53506	0.400851
train_distilbert_6d211fe6	TERMINATED		0.959277	0.994556	5.40791e-08	1.17333e-05	6.64995	1	271.444	0.609851	0.526802
train_distilbert_c980bae4	TERMINATED		0.99	0.993355	1e-07	5.21929e-06	2.51275	1	111.799	0.542276	0.324968
train_distilbert_6d0d29d6	TERMINATED		0.965773	0.995182	9.9752e-08	1.15549e-05	13.694	1	527.944	0.923802	0.549474
train_distilbert_b16ea82a	TERMINATED		0.952781	0.993931	2.93182e-08	1.19145e-05	3.2293	1	139.844	0.533466	0.451307
train_distilbert_eddf7cc0	TERMINATED		0.99	0.997109	8.13498e-08	1.28515e-05	15.5807	1	614.789	0.983285	0.56993
train_distilbert_43008974	TERMINATED		0.929089	0.993258	1e-07	1.03892e-05	12.0357	1	474.387	0.857461	0.520022
train_distilbert_b3408a4e	TERMINATED		0.99	0.993809	4.67441e-08	1.10418e-05	11.9165	1	474.126	0.828205	0.526164
train_distilbert_cfbfb220	TERMINATED		0.979454	0.9999	1e-07	1.49578e-05	20.3715
```

### Retrieve the results

```python
best_trial = analysis.get_best_trial(HP_METRIC, MODE, "all")
metric = best_trial.metric_analysis[HP_METRIC][MODE]
print(f"n_trials={len(analysis.trials)}")
print(f"time={time.time()-start_time}")
print(f"Best model eval {HP_METRIC}: {metric:.4f}")
print(f"Best model parameters: {best_trial.config}")
# n_trials=22
# time=3999.769361972809
# Best model eval matthews_correlation: 0.5699
# Best model parameters: {'num_train_epochs': 15.580684188655825, 'learning_rate': 1.2851507818900338e-05, 'adam_epsilon': 8.134982521948352e-08, 'adam_beta1': 0.99, 'adam_beta2': 0.9971094424784387}
```

[Link to notebook](https://github.com/microsoft/FLAML/blob/main/notebook/tune_huggingface.ipynb) | [Open in colab](https://colab.research.google.com/github/microsoft/FLAML/blob/main/notebook/tune_huggingface.ipynb)