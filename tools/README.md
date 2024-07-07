# Introduction

This directory contains a library of manually created python tools. These tools have three categories: math, data_analysis and information_retrieval.

# Directory Layout
```
tools
├── README.md
├── data_analysis
│   ├── calculate_correlation.py
│   └── ...
├── information_retrieval
│   ├── arxiv_download.py
│   ├── arxiv_search.py
│   └── ...
├── math
│   ├── calculate_circle_area_from_diameter.py
│   └── ...
└── tool_description.tsv
```

Tools can be imported from `tools/{category}/{tool_name}.py` with exactly the same function name.

`tool_description.tsv` contains descriptions of tools for retrieval.

# How to use
Some tools require Bing Search API key and RapidAPI key. For Bing API, you can read more about how to get an API on the [Bing Web Search API](https://www.microsoft.com/en-us/bing/apis/bing-web-search-api) page. For RapidAPI, you can [sign up](https://rapidapi.com/auth/sign-up) and subscribe to these two links([link1](https://rapidapi.com/illmagination/api/youtube-captions-and-transcripts/), [link2](https://rapidapi.com/420vijay47/api/youtube-mp3-downloader2/)). These apis have free billing options and there is no need to worry about extra costs.

To install the requirements for running tools, use pip install.
```bash
pip install -r tools/requirements.txt
```

Whenever you run the tool-related code, remember to export the api keys to system variables.
```bash
export BING_API_KEY=""
export RAPID_API_KEY=""
```
or
```python
import os
os.environ["BING_API_KEY"] = ""
os.environ["RAPID_API_KEY"] = ""
```
