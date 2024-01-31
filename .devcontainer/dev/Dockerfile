# Basic setup
FROM python:3.11-slim-bookworm

# Update and install necessary packages
RUN apt-get update && apt-get -y update
# added vim and nano for convenience
RUN apt-get install -y sudo git npm vim nano curl wget

# Setup a non-root user 'autogen' with sudo access
RUN adduser --disabled-password --gecos '' autogen
RUN adduser autogen sudo
RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
USER autogen
WORKDIR /home/autogen

# Set environment variable
# ENV OPENAI_API_KEY="{OpenAI-API-Key}"

# Clone the AutoGen repository
RUN git clone https://github.com/microsoft/autogen.git /home/autogen/autogen
WORKDIR /home/autogen/autogen

# Install AutoGen in editable mode with extra components
RUN sudo pip install -e .[test,teachable,lmm,retrievechat,mathchat,blendsearch]

# Install pre-commit hooks
RUN pre-commit install

# Setup Docusaurus and Yarn for the documentation website
RUN sudo npm install --global yarn
RUN sudo pip install pydoc-markdown
RUN cd website
RUN yarn install --frozen-lockfile --ignore-engines

RUN arch=$(arch | sed s/aarch64/arm64/ | sed s/x86_64/amd64/) && \
    wget -q https://github.com/quarto-dev/quarto-cli/releases/download/v1.4.549/quarto-1.4.549-linux-${arch}.tar.gz && \
    mkdir -p /home/autogen/quarto/ && \
    tar -xzf quarto-1.4.549-linux-${arch}.tar.gz --directory /home/autogen/quarto/ && \
    rm quarto-1.4.549-linux-${arch}.tar.gz

ENV PATH="${PATH}:/home/autogen/quarto/quarto-1.4.549/bin/"

# Exposes the Yarn port for Docusaurus
EXPOSE 3000

# Pre-load popular Python packages
RUN pip install numpy pandas matplotlib seaborn scikit-learn requests urllib3 nltk pillow pytest beautifulsoup4

# Set the default command to bash
CMD ["/bin/bash"]
