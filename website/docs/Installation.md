# Installation

## Setup Virtual Environment

When not using a docker container, we recommend using a virtual environment to install AutoGen. This will ensure that the dependencies for AutoGen are isolated from the rest of your system.

Using Venv
```bash
python3 -m venv autogen
source autogen/bin/activate
```

OR using conda
```bash
conda create -n autogen python=3.8
conda activate autogen
```

## Python

AutoGen requires **Python version >= 3.8**. It can be installed from pip:

Using pip
```bash
pip install pyautogen
```

or conda:
```bash
conda install -c conda-forge pyautogui
``` 

### Optional Dependencies
* docker

For the best user experience and seamless code execution, we highly recommend using Docker with AutoGen. Docker is a containerization platform that simplifies the setup and execution of your code. Developing in a docker container, such as GitHub Codespace, also makes the development convenient.

When running AutoGen out of a docker container, to use docker for code execution, you also need to install the python package `docker`:
```bash
pip install docker
```

Or using conda
```bash
conda install -c conda-forge docker
```

* blendsearch, retrievechat
```bash
pip install "pyautogen[blendsearch]"
pip install "pyautogen[retrievechat]"
```

Or using conda
* blendsearch, retrievechat
```bash
conda install -c conda-forge -c bioconda "pyautogen[blendsearch,retrievechat]"
``` 
