#-------------------------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See LICENSE file in the project root for license information.
#-------------------------------------------------------------------------------------------------------------

FROM mcr.microsoft.com/vscode/devcontainers/python:3.10

#
# Update the OS and maybe install packages
#
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
   && apt-get upgrade -y  \
   && apt-get -y install --no-install-recommends build-essential npm \
   && apt-get autoremove -y \
   && apt-get clean -y \
   && wget https://github.com/quarto-dev/quarto-cli/releases/download/v1.4.549/quarto-1.4.549-linux-amd64.deb \
   && dpkg -i quarto-1.4.549-linux-amd64.deb \
   && rm -rf /var/lib/apt/lists/* quarto-1.4.549-linux-amd64.deb
ENV DEBIAN_FRONTEND=dialog

# For docs
RUN npm install --global yarn
RUN pip install pydoc-markdown
RUN pip install pyyaml
RUN pip install colored
