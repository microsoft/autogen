# basic setup
FROM python:3.10

# Change the mirror server in the Dockerfile to use one that might be more reliable or closer to your geographical location.
RUN echo 'deb http://ftp.debian.org/debian/ bookworm main' > /etc/apt/sources.list && \
    apt-get update && \
    apt-get -y upgrade && \
    apt-get install -y sudo git npm && \
    apt-get clean

# Setup user to not run as root
RUN adduser --disabled-password --gecos '' autogen-dev
RUN adduser autogen-dev sudo
RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
USER autogen-dev

# Pull repo
RUN cd /home/autogen-dev && git clone https://github.com/microsoft/autogen.git
WORKDIR /home/autogen-dev/autogen

# Install autogen (Note: extra components can be installed if needed)
RUN sudo pip install -e .[test]

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
