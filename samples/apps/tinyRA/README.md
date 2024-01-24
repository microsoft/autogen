# TinyRA

[![PyPI version](https://badge.fury.io/py/tinyra.svg)](https://badge.fury.io/py/tinyra)
[![Downloads](https://static.pepy.tech/badge/tinyra/week)](https://pepy.tech/project/tinyra)

TinyRA is a minimalistic Research Assistant built with AutoGen agents.

## Installation

To install TinyRA, clone the repository and install it using pip:

```
cd samples/app/tinyRA
pip install -e .
```

TinyRA requires that your system have `tmux` installed. Currently tested with `conda` and `virtualenv`.

## Usage

TinyRA expects an environment variable called `OAI_CONFIG_LIST` or a file called `OAI_CONFIG_LIST` in the current working directory.
 Either way, you can set these according to instructions [here](https://github.com/microsoft/autogen#quickstart).

(Optional) You can give TinyRA access to your name by setting the `TINYRA_USER` environment variable. For example
```
export TINYRA_USER=Bob
```
If this is not set, the interface will use the `USER` environment variable set by your operating system.

Once you have setup your configuration, you can run TinyRA with the following command:

```
tinyra
```

_Note_: TinyRA will create a new directory in your system at `~/.tinyra`. This directory contains database(s), logs, and work directory that is shared between you and TinyRA.



You can reset the chat history of TinyRA via the following command:

```
tinyra --reset
```
This will delete all chat history. You will be prompted to confirm this action.
If you want to reset the chat history and delete the data path, use the following command:


```
tinyra --reset-all
```

This will delete all chat history and the data path. You will be prompted to confirm this action.
