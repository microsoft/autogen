FROM mcr.microsoft.com/devcontainers/python:3.11
MAINTAINER AutoGen

# Install packages
# ffmpeg and exiftool are needed for mdconvert
RUN apt-get update && apt-get install ffmpeg exiftool -y

# Set the image to the Pacific Timezone
RUN ln -snf /usr/share/zoneinfo/US/Pacific /etc/localtime && echo "US/Pacific" > /etc/timezone

# Upgrade pip
RUN pip install --upgrade pip

# Pre-load autogen to get the dependencies, but then uninstall them (leaving dependencies in place)
RUN pip install autogen-core autogen-agentchat autogen-ext pyyaml
RUN pip uninstall --yes autogen-core autogen-agentchat autogen-ext

# Optional markitdown dependencies
RUN pip install markitdown SpeechRecognition pydub youtube_transcript_api==0.6.0

# Pre-load popular packages as per https://learnpython.com/blog/most-popular-python-packages/
RUN pip install numpy pandas matplotlib seaborn scikit-learn requests urllib3 nltk pytest

# Pre-load Playwright
RUN pip install playwright
RUN playwright install --with-deps chromium

# Webarena (evaluation code)
#RUN pip install beartype aiolimiter
#RUN /usr/bin/echo -e "import nltk\nnltk.download('punkt')" | python
