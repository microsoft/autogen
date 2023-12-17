# TinyRA

TinyRA is a minimalistic Research Assistant built with AutoGen agents.

## Installation

To install TinyRA, clone the repository and install it using pip:

```
cd samples/app/tinyRA
pip install -e .
```

## Usage

You can run TinyRA with the following command:

```
tinyra
```

By default, TinyRA uses the configuration file at `./OAI_CONFIG_LIST` and the working directory `./coding`. You can specify a different config file or working directory with the `-c` and `-w` options, respectively:

```
tinyra -c path/to/config -w path/to/workdir
```

## Help

You can display the help message with the `-h` option:

```
tinyra -h
```

This will display the usage information and the available options.
