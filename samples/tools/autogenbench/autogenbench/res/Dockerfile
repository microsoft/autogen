FROM python:3.11
MAINTAINER AutoGen

# Install packages
RUN apt-get update && apt-get install ffmpeg exiftool -y

# Set the image to the Pacific Timezone
RUN ln -snf /usr/share/zoneinfo/US/Pacific /etc/localtime && echo "US/Pacific" > /etc/timezone

# Upgrade pip
RUN pip install --upgrade pip

# Pre-load autogen dependencies, but not autogen itself since we'll often want to install the latest from source
RUN pip install pyautogen[teachable,lmm,graphs,websurfer]
RUN pip uninstall --yes pyautogen

# Pre-load popular packages as per https://learnpython.com/blog/most-popular-python-packages/
RUN pip install numpy pandas matplotlib seaborn scikit-learn requests urllib3 nltk pillow pytest

# Pre-load packages needed for complex_task file utils
RUN pip install python-docx pdfminer.six requests pillow easyocr python-pptx SpeechRecognition pandas openpyxl pydub mammoth puremagic youtube_transcript_api==0.6.0

# Pre-load the OCR model
RUN /usr/bin/echo -e "import easyocr\nreader = easyocr.Reader(['en'])" | python
