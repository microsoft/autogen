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
1. For the best user experience and seamless code execution, we highly recommend using Docker with AutoGen. 
2. Docker is a containerization platform that simplifies the setup and execution of your code. 
3. If you're working in a GitHub Codespace environment, AutoGen make a easy development in environment with Docker container, which is convenient to use.

 To use docker for code execution, you also need to install the python package `docker`:
```bash
pip install docker
```

* blendsearch
```bash
pip install "pyautogen[blendsearch]"
```
