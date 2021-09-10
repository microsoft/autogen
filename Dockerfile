# basic setup
FROM python:3.7
RUN apt-get update && apt-get -y update
RUN apt-get install -y sudo git

# Setup user to not run as root
RUN adduser --disabled-password --gecos '' hb-dev
RUN adduser hb-dev sudo
RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
USER flaml-dev

# Pull repo
RUN cd /home/flaml-dev && git clone https://github.com/microsoft/FLAML.git
WORKDIR /home/flaml-dev/FLAML

# Install FLAML (Note: extra components can be installed if needed)
RUN sudo pip install -e .[test,notebook]

# Install precommit hooks
RUN pre-commit install

# override default image starting point
CMD /bin/bash
ENTRYPOINT []