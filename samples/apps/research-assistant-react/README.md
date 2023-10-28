# ARA - AutoGen Research Assistant

ARA is an Autogen-powered AI research assistant that can converse with you to help you conduct research, write and execute code, run saved skills, learn new skills by demonstration, and adapt in response to your interactions.

Project Structure:

- _backend/_ code for the web api, served by FastAPI.
- _frontend/_ code for the webui, built with Gatsby and Tailwind

## Getting Started

Install requirements:

```bash
cd backend
pip install -r requirements.txt
```

AutoGen requires access to an LLM. Please see the [AutoGen docs](https://microsoft.github.io/autogen/docs/FAQ#set-your-api-endpoints) on how to configure access to your LLM. We recommend setting the `OAI_CONFIG_LIST` environment variable to point to your LLM config file.

Also, if you plan to use bing search, set the `BING_API_KEY`

```bash
export OAI_CONFIG_LIST=/path/to/OAI_CONFIG_LIST
export BING_API_KEY=<your bing api key>
```

Run the web ui:

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Navigate to <http://localhost:8000/> to view the web ui.

To update the web ui, navigate to the frontend directory, make changes and rebuild the ui.

## Acknowledgements

Based on the [AutoGen](https://microsoft.github.io/autogen) project.
Adapted in October 2023 from a research prototype (original credits: Gagan Bansal, Adam Fourney, Victor Dibia, Piali Choudhury, Saleema Amershi, Ahmed Awadallah, Chi Wang)
