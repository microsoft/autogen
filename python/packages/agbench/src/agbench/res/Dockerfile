FROM mcr.microsoft.com/devcontainers/python:3.11
MAINTAINER AutoGen

# Install packages
# ffmpeg and exiftool are needed for mdconvert
RUN apt-get update && apt-get install ffmpeg exiftool -y

# Set the image to the Pacific Timezone
RUN ln -snf /usr/share/zoneinfo/US/Pacific /etc/localtime && echo "US/Pacific" > /etc/timezone

# Upgrade pip
RUN pip install --upgrade pip

# Pre-load autogen_core dependencies, but not autogen_core itself since we'll often want to install the latest from source
RUN pip install openai pillow aiohttp typing-extensions pydantic types-aiofiles grpcio protobuf

# Pre-load popular packages as per https://learnpython.com/blog/most-popular-python-packages/
RUN pip install numpy pandas matplotlib seaborn scikit-learn requests urllib3 nltk pytest

# Pre-load packages needed for mdconvert file utils
RUN pip install python-docx pdfminer.six python-pptx SpeechRecognition openpyxl pydub mammoth puremagic youtube_transcript_api==0.6.0

# Pre-load Playwright
RUN pip install playwright
RUN playwright install --with-deps chromium

# Fix an incompatibility with numpy
RUN pip uninstall --yes numpy
RUN pip install "numpy<2.0"

# Webarena (evaluation code)
RUN pip install beartype aiolimiter
RUN /usr/bin/echo -e "import nltk\nnltk.download('punkt')" | python
