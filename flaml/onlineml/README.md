# ChaCha for Online AutoML

FLAML includes *ChaCha* which is an automatic hyperparameter tuning solution for online machine learning. Online machine learning has the following properties: (1) data comes in sequential order; and (2) the performance of the machine learning model is evaluated online, i.e., at every iteration. *ChaCha* performs online AutoML respecting the aforementioned properties of online learning, and at the same time respecting the following constraints: (1) only a small constant number of 'live' models are allowed to perform online learning at the same time;  and (2) no model persistence or offline training is allowed, which means that once we decide to replace a 'live' model with a new one, the replaced model can no longer be retrieved.

For more technical details about *ChaCha*, please check our paper.

* [ChaCha for Online AutoML](https://www.microsoft.com/en-us/research/publication/chacha-for-online-automl/). Qingyun Wu, Chi Wang, John Langford, Paul Mineiro and Marco Rossi. ICML 2021.
```
@inproceedings{wu2021chacha,
    title={ChaCha for online AutoML},
    author={Qingyun Wu and Chi Wang and John Langford and Paul Mineiro and Marco Rossi},
    year={2021},
    booktitle={ICML},
}
```

## `AutoVW`

`flaml.AutoVW` is a realization of *ChaCha* AutoML method with online learners from the open-source online machine learning library [Vowpal Wabbit](https://vowpalwabbit.org/) learner. It can be used to tune both conventional numerical and categorical hyperparameters, such as learning rate, and hyperparameters for featurization choices, such as the namespace (a namespace is a group of features) interactions in Vowpal Wabbit.

An example of online namespace interactions tuning in VW:

```python
# require: pip install flaml[vw]
from flaml import AutoVW
'''create an AutoVW instance for tuning namespace interactions'''
autovw = AutoVW(max_live_model_num=5, search_space={'interactions': AutoVW.AUTOMATIC})
```

An example of online tuning of both namespace interactions and learning rate in VW:

```python
# require: pip install flaml[vw]
from flaml import AutoVW
from flaml.tune import loguniform
''' create an AutoVW instance for tuning namespace interactions and learning rate'''
# set up the search space and init config
search_space_nilr = {'interactions': AutoVW.AUTOMATIC, 'learning_rate': loguniform(lower=2e-10, upper=1.0)}
init_config_nilr = {'interactions': set(), 'learning_rate': 0.5}
# create an AutoVW instance
autovw = AutoVW(max_live_model_num=5, search_space=search_space_nilr, init_config=init_config_nilr)
```

A user can use the resulting AutoVW instances `autovw` in a similar way to a vanilla Vowpal Wabbit instance, i.e., `pyvw.vw`, to perform online learning by iteratively calling its `predict(data_example)` and `learn(data_example)` functions at each data example.

For more examples, please check out
[AutoVW notebook](https://github.com/microsoft/FLAML/blob/main/notebook/autovw.ipynb).
