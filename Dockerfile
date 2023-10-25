# basic setup
FROM python:3.10
RUN apt-get update && apt-get -y update
RUN apt-get install -y sudo git npm

# Setup user to not run as root
RUN adduser --disabled-password --gecos '' autogen-dev
RUN adduser autogen-dev sudo
RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
USER autogen-dev


