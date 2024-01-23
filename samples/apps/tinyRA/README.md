# TinyRA

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

Once you have setup your configuration, you can run TinyRA with the following command:

```
tinyra
```

_Note_: TinyRA will create a new directory in your system at `~/.tinyra`. This directory contains database(s), logs, and work directory that is shared between you and TinyRA.

You can reset TinyRA via the following command:

```
tinyra reset
```
