#-------------------------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for license information.
#-------------------------------------------------------------------------------------------------------------

FROM mcr.microsoft.com/vscode/devcontainers/python:0-3.10

#
# Update the OS and maybe install packages
#
ENV UBUNTU_FRONTEND=interactive
RUN apt-get update \
   && apt-get upgrade -y  \
   && apt-get -y install --no-install-recommends build-essential npm \
   && apt-get autoremove -y \
   && apt-get clean -y \
   && rm -rf /var/lib/apt/lists/*
ENV UBUNTU_FRONTEND=dialog

# For docs
RUN npm install --global yarn
RUN pip install pydoc-markdown
