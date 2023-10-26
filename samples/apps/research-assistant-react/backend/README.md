## FastAPI Backend for AutoGen Research Assistant

### Installation

`pip install -r requirements.txt`

### Initialize Database

`python setup_db.py`

### Setup OAI Config

Create a file called `OAI_CONFIG_LIST` in `backend` with the following (JSON) format.
AutoGen can read this file and use it to initialize the OpenAI API.
This file is just an example, please use appropriate model names and api keys.
Ensure that any filters used in `CONFIG_LIST` are consistent with this file.
Keys should be inserted in the order you want the models to be used-- the most preferred model should be on the top.

```json
[
  {
    "model": "gpt-3.5-turbo-16k",
    "api_key": "<your OpenAI API key here>"
  },
  {
    "model": "gpt-4-32k",
    "api_key": "<your OpenAI API key here>"
  },
  {
    "model": "gpt-4",
    "api_key": "<your Azure OpenAI API key here>",
    "api_base": "<your Azure OpenAgit usI API base here>",
    "api_type": "azure",
    "api_version": "2023-06-01-preview"
  },
  {
    "model": "gpt-4-32k-0314",
    "api_key": "<your Azure OpenAI API key here>",
    "api_base": "<your Azure OpenAI API base here>",
    "api_type": "azure",
    "api_version": "2023-06-01-preview"
  }
]
```

### Run

`uvicorn main:app --reload`

Note: Use the `/api/docs` endpoint to interact with the API.
