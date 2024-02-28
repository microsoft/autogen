FROM mcr.microsoft.com/devcontainers/dotnet:8.0
# Install the xz-utils package
RUN apt-get update && apt-get install -y xz-utils ca-certificates curl gnupg

RUN curl -fsSL https://aka.ms/install-azd.sh | bash