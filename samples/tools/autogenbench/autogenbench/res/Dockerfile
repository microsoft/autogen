# Host a jsPsych experiment in Azure
FROM python:3.11
MAINTAINER AutoGen

# Upgrade pip
RUN pip install --upgrade pip

# Set the image to the Pacific Timezone
RUN ln -snf /usr/share/zoneinfo/US/Pacific /etc/localtime && echo "US/Pacific" > /etc/timezone

# Pre-load autogen dependencies, but not autogen itself since we'll often want to install the latest from source
RUN pip install autogen-agentchat[teachable,lmm,graphs,websurfer]~=0.2
RUN pip uninstall --yes autogen-agentchat~=0.2

# Pre-load popular packages as per https://learnpython.com/blog/most-popular-python-packages/
RUN pip install numpy pandas matplotlib seaborn scikit-learn requests urllib3 nltk pillow pytest
