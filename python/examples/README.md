# Examples

This directory contains examples of how to use AGNext.

First, you need a shell with AGNext and the examples dependencies installed. To do this, run:

```bash
hatch shell
```

To run an example, just run the corresponding Python script. For example, to run the `coder_reviewer.py` example, run:

```bash
hatch shell
python coder_reviewer.py
```

Or simply:
```bash
hatch run python coder_reviewer.py
```

To enable logging, turn on verbose mode by setting `--verbose` flag:

```bash
hatch run python coder_reviewer.py --verbose
```

By default the log file is saved in the same directory with the same filename
as the script, e.g., "coder_reviewer.log".
