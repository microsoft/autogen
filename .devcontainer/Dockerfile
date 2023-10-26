FROM mcr.microsoft.com/devcontainers/dotnet:0-7.0
# Install the xz-utils package
RUN apt-get update && apt-get install -y xz-utils nodejs npm

RUN curl -fsSL https://aka.ms/install-azd.sh | bash

RUN curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | \
  sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null && \
  echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | \
  sudo tee /etc/apt/sources.list.d/ngrok.list && \
  sudo apt update && sudo apt install ngrok

RUN npm i -g azure-functions-core-tools@4 --unsafe-perm true