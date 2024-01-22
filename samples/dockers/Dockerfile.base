FROM python:3.11-slim-bookworm

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        software-properties-common sudo\
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Setup a non-root user 'autogen' with sudo access
RUN adduser --disabled-password --gecos '' autogen
RUN adduser autogen sudo
RUN echo '%sudo ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
USER autogen
WORKDIR /home/autogen

# Set environment variable if needed
# ENV OPENAI_API_KEY="{OpenAI-API-Key}"

# Pre-load popular packages as per https://learnpython.com/blog/most-popular-python-packages/
RUN pip install pyautogen numpy pandas matplotlib seaborn scikit-learn requests urllib3 nltk pillow pytest beautifulsoup4

# Expose port
# EXPOSE 8081

# Start Command
CMD [ "/bin/bash" ]
