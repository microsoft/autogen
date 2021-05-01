# Economical Hyperparameter Optimization

`flaml.tune` is a module for economical hyperparameter tuning. It frees users from manually tuning many hyperparameters for a software, such as machine learning training procedures. 
It can be used standalone, or together with ray tune or nni.

* Example for sequential tuning (recommended when compute resource is limited and each trial can consume all the resources):

```python
# require: pip install flaml[blendsearch]
from flaml import tune
import time

def evaluate_config(config):
    '''evaluate a hyperparameter configuration'''
    # we uss a toy example with 2 hyperparameters
    metric = (round(config['x'])-85000)**2 - config['x']/config['y']
    # usually the evaluation takes an non-neglible cost
    # and the cost could be related to certain hyperparameters
    # in this example, we assume it's proportional to x
    time.sleep(config['x']/100000)
    # use tune.report to report the metric to optimize    
    tune.report(metric=metric) 

analysis = tune.run(
    evaluate_config,    # the function to evaluate a config
    config={
        'x': tune.qloguniform(lower=1, upper=100000, q=1),
        'y': tune.randint(lower=1, upper=100000)
    }, # the search space
    low_cost_partial_config={'x':1},    # a initial (partial) config with low cost
    metric='metric',    # the name of the metric used for optimization
    mode='min',         # the optimization mode, 'min' or 'max'
    num_samples=-1,    # the maximal number of configs to try, -1 means infinite
    time_budget_s=60,   # the time budget in seconds
    local_dir='logs/',  # the local directory to store logs
    # verbose=0,          # verbosity    
    # use_ray=True, # uncomment when performing parallel tuning using ray
    )

print(analysis.best_trial.last_result)  # the best trial's result
print(analysis.best_config) # the best config
```

* Example for using ray tune's API:

```python
# require: pip install flaml[blendsearch] ray[tune]
from ray import tune as raytune
from flaml import CFO, BlendSearch
import time

def evaluate_config(config):
    '''evaluate a hyperparameter configuration'''
    # we use a toy example with 2 hyperparameters
    metric = (round(config['x'])-85000)**2 - config['x']/config['y']
    # usually the evaluation takes a non-neglible cost
    # and the cost could be related to certain hyperparameters
    # in this example, we assume it's proportional to x
    time.sleep(config['x']/100000)
    # use tune.report to report the metric to optimize    
    tune.report(metric=metric) 

analysis = raytune.run(
    evaluate_config,    # the function to evaluate a config
    config={
        'x': tune.qloguniform(lower=1, upper=100000, q=1),
        'y': tune.randint(lower=1, upper=100000)
    }, # the search space
    metric='metric',    # the name of the metric used for optimization
    mode='min',         # the optimization mode, 'min' or 'max'
    num_samples=-1,    # the maximal number of configs to try, -1 means infinite
    time_budget_s=60,   # the time budget in seconds
    local_dir='logs/',  # the local directory to store logs
    search_alg=CFO(low_cost_partial_config=[{'x':1}]) # or BlendSearch
    )

print(analysis.best_trial.last_result)  # the best trial's result
print(analysis.best_config) # the best config
```

* Example for using NNI: An example of using BlendSearch with NNI can be seen in [test](https://github.com/microsoft/FLAML/tree/main/test/nni). CFO can be used as well in a similar manner. To run the example, first make sure you have [NNI](https://nni.readthedocs.io/en/stable/) installed, then run:

```shell
$nnictl create --config ./config.yml
```

* For more examples, please check out 
[notebooks](https://github.com/microsoft/FLAML/tree/main/notebook/).


`flaml` offers two HPO methods: CFO and BlendSearch. 
`flaml.tune` uses BlendSearch by default.

## CFO: Frugal Optimization for Cost-related Hyperparameters

<p align="center">
    <img src="https://github.com/microsoft/FLAML/blob/main/docs/images/CFO.png"  width=200>
    <br>
</p>

CFO uses the randomized direct search method FLOW<sup>2</sup> with adaptive stepsize and random restart. 
It requires a low-cost initial point as input if such point exists.
The search begins with the low-cost initial point and gradually move to
high cost region if needed. The local search method has a provable convergence
rate and bounded cost. 

About FLOW<sup>2</sup>: FLOW<sup>2</sup> is a simple yet effective randomized direct search method. 
It is an iterative optimization method that can optimize for black-box functions.
FLOW<sup>2</sup> only requires pairwise comparisons between function values to perform iterative update. Comparing to existing HPO methods, FLOW<sup>2</sup> has the following appealing properties:
1. It is applicable to general black-box functions with a good convergence rate in terms of loss.
3. It provides theoretical guarantees on the total evaluation cost incurred.

The GIFs attached below demostrates an example search trajectory of FLOW<sup>2</sup> shown in the loss and evaluation cost (i.e., the training time ) space respectively. From the demonstration, we can see that (1) FLOW<sup>2</sup> can quickly move toward the low-loss region, showing good convergence property and (2) FLOW<sup>2</sup> tends to avoid exploring the high-cost region until necessary.

<p align="center">
    <img align="center", src="https://github.com/microsoft/FLAML/blob/main/docs/images/heatmap_loss_cfo_12s.gif"  width=360>  <img align="center", src="https://github.com/microsoft/FLAML/blob/main/docs/images/heatmap_cost_cfo_12s.gif"  width=360> 
    <br>
    <figcaption>Figure 1. FLOW<sup>2</sup> in tuning the # of leaves and the # of trees for XGBoost. The two background heatmaps show the loss and cost distribution of all configurations. The black dots are the points evaluated in FLOW<sup>2</sup>. Black dots connected by lines are points that yield better loss performance when evaluated.</figcaption>
</p>


Example:

```python
from flaml import CFO
tune.run(...
    search_alg = CFO(low_cost_partial_config=low_cost_partial_config),
)
```

Recommended scenario: there exist cost-related hyperparameters and a low-cost
initial point is known before optimization. 
If the search space is complex and CFO gets trapped into local optima, consider
using BlendSearch. 

## BlendSearch: Economical Hyperparameter Optimization With Blended Search Strategy

<p align="center">
    <img src="https://github.com/microsoft/FLAML/blob/main/docs/images/BlendSearch.png"  width=200>
    <br>
</p>

BlendSearch combines local search with global search. It leverages the frugality
of CFO and the space exploration ability of global search methods such as
Bayesian optimization. Like CFO, BlendSearch requires a low-cost initial point
as input if such point exists, and starts the search from there. Different from
CFO, BlendSearch will not wait for the local search to fully converge before 
trying new start points. The new start points are suggested by the global search
method and filtered based on their distance to the existing points in the
cost-related dimensions. BlendSearch still gradually increases the trial cost.
It prioritizes among the global search thread and multiple local search threads
based on optimism in face of uncertainty.

Example:

```python
# require: pip install flaml[blendsearch]
from flaml import BlendSearch
tune.run(...
    search_alg = BlendSearch(low_cost_partial_config=low_cost_partial_config),
)
```

- Recommended scenario: cost-related hyperparameters exist, a low-cost
initial point is known, and the search space is complex such that local search
is prone to be stuck at local optima.


- Suggestion about using larger search space in BlendSearch: 
In hyperparameter optimization, a larger search space is desirable because it is more likely to include the optimal configuration (or one of the optimal configurations) in hindsight. However the performance (especially anytime performance) of most existing HPO methods is undesirable if the cost of the configurations in the search space has a large variation. Thus hand-crafted small search spaces (with relatively homogeneous cost) are often used in practice for these methods, which is subject to idiosyncrasy. BlendSearch combines the benefits of local search and global search, which enables a smart (economical) way of deciding where to explore in the search space even though it is larger than necessary. This allows users to specify a larger search space in BlendSearch, which is often easier and a better practice than narrowing down the search space by hand.

For more technical details, please check our papers.

* [Frugal Optimization for Cost-related Hyperparameters](https://arxiv.org/abs/2005.01571). Qingyun Wu, Chi Wang, Silu Huang. AAAI 2021.

```
@inproceedings{wu2021cfo,
    title={Frugal Optimization for Cost-related Hyperparameters},
    author={Qingyun Wu and Chi Wang and Silu Huang},
    year={2021},
    booktitle={AAAI'21},
}
```

* [Economical Hyperparameter Optimization With Blended Search Strategy](https://www.microsoft.com/en-us/research/publication/economical-hyperparameter-optimization-with-blended-search-strategy/). Chi Wang, Qingyun Wu, Silu Huang, Amin Saied. ICLR 2021.

```
@inproceedings{wang2021blendsearch,
    title={Economical Hyperparameter Optimization With Blended Search Strategy},
    author={Chi Wang and Qingyun Wu and Silu Huang and Amin Saied},
    year={2021},
    booktitle={ICLR'21},
}
```