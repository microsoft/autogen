# Installation

## Python

AutoGen requires **Python version >= 3.8**. It can be installed from pip:

```bash
pip install pyautogen
```
<!--
or conda:
```
conda install pyautogen -c conda-forge
``` -->

### Optional Dependencies
* docker
We strongly recommend using docker for code execution or running AutoGen in a docker container (e.g., when developing in GitHub codespace, the autogen runs in a docker container). To use docker for code execution, you also need to install the python package `docker`:
```bash
pip install docker
```

* blendsearch
```bash
pip install "pyautogen[blendsearch]"
```
