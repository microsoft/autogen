import os
import setuptools

here = os.path.abspath(os.path.dirname(__file__))

with open("README.md", "r", encoding="UTF-8") as fh:
    long_description = fh.read()

version = {}
with open(os.path.join(here, "version.py")) as fp:
    exec(fp.read(), version)
__version__ = version["__version__"]

install_requires = [
    "numpy",  # mdconvert
    "beautifulsoup4",
    "markdownify",
    "pathvalidate",
    "puremagic",  # File identification
    "binaryornot",  # More file identification
    "pdfminer.six",  # Pdf
    "mammoth",  # Docx
    "python-pptx",  # Ppts
    "pandas",  # Xlsx
    "openpyxl",
    "youtube_transcript_api==0.6.0",  # Transcription
    "easyocr"
]

setuptools.setup(
    name="screen_parsing",
    version=__version__,
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(exclude=("tests",)),
    package_data={
        "screen_parsing": ["static/*"],
    },
    include_package_data=True,
    install_requires=install_requires,
    extras_require={
        "test": [
            "pytest>=6.1.1,<8",
        ],
    },
    python_requires=">=3.10, <3.13",
)
