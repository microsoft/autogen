# Basic setup
FROM python:3.11-slim-bookworm

# add git lfs to apt
RUN curl -s https://packagecloud.io/install/repositories/github/git-lfs/script.deb.sh | bash

# Update and install necessary packages
RUN apt-get update && apt-get -y update
# added vim and nano for convenience
RUN apt-get install -y sudo git npm vim nano curl wget git-lfs

# Setup a non-root user 'autogen' with sudo access
RUN adduser --home /home/autogenhub --disabled-password --gecos '' autogen
RUN adduser autogen sudo
RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
USER autogen
WORKDIR /home/autogenhub

# Set environment variable
# ENV OPENAI_API_KEY="{OpenAI-API-Key}"

# Clone the AutoGen repository
RUN git clone https://github.com/autogenhub/autogen.git /home/autogenhub/autogen
WORKDIR /home/autogenhub/autogen

# Install AutoGen in editable mode with extra components
RUN sudo pip install --upgrade pip && \
    sudo pip install -e .[test,teachable,lmm,retrievechat,mathchat,blendsearch] && \
    pip install pytest-xdist pytest-cov

# Install pre-commit hooks
RUN pre-commit install

# Setup Docusaurus and Yarn for the documentation website
RUN sudo npm install --global yarn
RUN sudo pip install pydoc-markdown
RUN cd website
RUN yarn install --frozen-lockfile --ignore-engines

RUN arch=$(arch | sed s/aarch64/arm64/ | sed s/x86_64/amd64/) && \
    wget -q https://github.com/quarto-dev/quarto-cli/releases/download/v1.5.23/quarto-1.5.23-linux-${arch}.tar.gz && \
    mkdir -p /home/autogenhub/quarto/ && \
    tar -xzf quarto-1.5.23-linux-${arch}.tar.gz --directory /home/autogenhub/quarto/ && \
    rm quarto-1.5.23-linux-${arch}.tar.gz

ENV PATH="${PATH}:/home/autogenhub/quarto/quarto-1.5.23/bin/"

# Exposes the Yarn port for Docusaurus
EXPOSE 3000

# Pre-load popular Python packages
RUN pip install numpy pandas matplotlib seaborn scikit-learn requests urllib3 nltk pillow pytest beautifulsoup4

# Set the default command to bash
CMD ["/bin/bash"]
