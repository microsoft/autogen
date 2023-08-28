FROM mcr.microsoft.com/devcontainers/dotnet:0-7.0
# Install the xz-utils package
RUN apt-get update && apt-get install -y xz-utils nodejs npm

RUN curl -fsSL https://aka.ms/install-azd.sh | bash

RUN npm i -g azure-functions-core-tools@4 --unsafe-perm true