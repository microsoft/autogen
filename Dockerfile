# basic setup
FROM python:3.7
RUN apt-get update && apt-get -y update
RUN apt-get install -y sudo git npm

# Install Spark
RUN sudo apt-get update && sudo apt-get install -y --allow-downgrades --allow-change-held-packages --no-install-recommends \
        ca-certificates-java ca-certificates openjdk-17-jdk-headless \
        wget \
    && sudo apt-get clean && sudo rm -rf /var/lib/apt/lists/*
RUN wget --progress=dot:giga "https://www.apache.org/dyn/closer.lua/spark/spark-3.3.0/spark-3.3.0-bin-hadoop2.tgz?action=download" -O - | tar -xzC /tmp; archive=$(basename "spark-3.3.0/spark-3.3.0-bin-hadoop2.tgz") bash -c "sudo mv -v /tmp/\${archive/%.tgz/} /spark"
ENV SPARK_HOME=/spark \
    PYTHONPATH=/spark/python/lib/py4j-0.10.9.5-src.zip:/spark/python
ENV PATH="${PATH}:${SPARK_HOME}/bin"

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
