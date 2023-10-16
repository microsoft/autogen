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

For the best user experience and seamless code execution, we highly recommend using Docker with AutoGen. Docker is a containerization platform that simplifies the setup and execution of your code. Developing in a docker container, such as GitHub Codespace, also makes the development convenient.

When running AutoGen out of a docker container, to use docker for code execution, you also need to install the python package `docker`:
```bash
pip install docker
```

* blendsearch
```bash
pip install "pyautogen[blendsearch]"
```
