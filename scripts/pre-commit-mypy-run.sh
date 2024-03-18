#!/usr/bin/env bash

# taken from: https://jaredkhan.com/blog/mypy-pre-commit

# A script for running mypy,
# with all its dependencies installed.

set -o errexit

# Change directory to the project root directory.
cd "$(dirname "$0")"/..

# Install the dependencies into the mypy env.
# Note that this can take seconds to run.
# In my case, I need to use a custom index URL.
# Avoid pip spending time quietly retrying since
# likely cause of failure is lack of VPN connection.
# pip install --editable ".[types]"\
#  --retries 1 \
#  --no-input \
#  --quiet

mypy
