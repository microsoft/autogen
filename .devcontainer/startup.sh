#!/bin/bash

# dotnet setup
dotnet workload update
dotnet dev-certs https --trust

# python setup
pushd python
pip install uv
uv sync
source .venv/bin/activate
echo "export PATH=$PATH" >> ~/.bashrc
popd
