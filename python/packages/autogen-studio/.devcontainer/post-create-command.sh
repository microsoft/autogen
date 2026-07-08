#!/bin/bash

# Create the node_modules directory in the frontend folder if it doesn't exist
# This ensures the directory exists before mounting
mkdir -p frontend/node_modules

# Change ownership of node_modules to vscode user
# This prevents permission issues when installing packages
sudo chown vscode frontend/node_modules 

# Initialize git-lfs and fetch/checkout LFS files
git lfs install
git lfs fetch --all
git lfs checkout


pip install --upgrade pip gunicorn

# Install the AutoGen Studio project in editable mode (-e flag)
# This allows for development changes to be reflected immediately
pip install -e .

npm install -g gatsby-cli@latest

# Install yarn dependencies with cache to improve performance
cd frontend && \
yarn install --cache-folder /tmp/.yarn-cache