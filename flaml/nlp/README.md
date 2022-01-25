# AutoML for NLP

This directory contains utility functions used by AutoNLP. Currently we support four NLP tasks: sequence classification, sequence regression, multiple choice and summarization.

Please refer to this [link](https://microsoft.github.io/FLAML/docs/Examples/AutoML-NLP) for examples.


# Troubleshooting fine-tuning HPO for pre-trained language models

The frequent updates of transformers may lead to fluctuations in the results of tuning. To help users quickly troubleshoot the result of AutoNLP when a tuning failure occurs (e.g., failing to reproduce previous results), we have provided the following jupyter notebook:

* [Troubleshooting HPO for fine-tuning pre-trained language models](https://github.com/microsoft/FLAML/blob/main/notebook/research/acl2021.ipynb)

Our findings on troubleshooting fine-tuning the Electra and RoBERTa model for the GLUE dataset can be seen in the following paper published in ACL 2021:

* [An Empirical Study on Hyperparameter Optimization for Fine-Tuning Pre-trained Language Models](https://arxiv.org/abs/2106.09204). Xueqing Liu, Chi Wang. ACL-IJCNLP 2021.

```bibtex
@inproceedings{liu2021hpo,
    title={An Empirical Study on Hyperparameter Optimization for Fine-Tuning Pre-trained Language Models},
    author={Xueqing Liu and Chi Wang},
    year={2021},
    booktitle={ACL-IJCNLP},
}
```


