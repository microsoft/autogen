# basic setup
FROM python:3.7
RUN apt-get update && apt-get -y update
RUN apt-get install -y sudo git npm

# Setup user to not run as root
RUN adduser --disabled-password --gecos '' flaml-dev
RUN adduser flaml-dev sudo
RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
USER flaml-dev

# Pull repo
RUN cd /home/flaml-dev && git clone https://github.com/microsoft/FLAML.git
WORKDIR /home/flaml-dev/FLAML

# Install FLAML (Note: extra components can be installed if needed)
RUN sudo pip install -e .[test,notebook]

# Install precommit hooks
RUN pre-commit install

# For docs
RUN sudo npm install --global yarn
RUN sudo pip install pydoc-markdown
RUN cd website
RUN yarn install --frozen-lockfile --ignore-engines

# override default image starting point
CMD /bin/bash
ENTRYPOINT []
