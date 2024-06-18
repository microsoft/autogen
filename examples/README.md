# Examples

This directory contains examples of how to use AGNext.

First, you need to install AGNext and development dependencies by running the
following command:

```bash
pip install -e '.[dev]'
```

To run an example, just run the corresponding Python script. For example, to run the `coder_reviewer.py` example, run:

```bash
python coder_reviewer.py
```

To enable logging, turn on verbose mode by setting `--verbose` flag:

```bash
python coder_reviewer.py --verbose
```

By default the log file is saved in the same directory with the same filename
as the script, e.g., "coder_reviewer.log".
