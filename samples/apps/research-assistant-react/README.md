# ARA - AutoGen Research Assistant

![ARA](./docs/images/ara.png)
ARA is an Autogen-powered AI research assistant that can converse with researchers, write and execute code, run saved skills, learn new skills by demonstration, and adapt in response to user interactions.

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
export OAI_CONFIG_LIST=/path/to/llm/config
export BING_API_KEY=<your bing api key>
```

Run the web ui:

```bash
cd backend
uvicorn main:app --reload --port 8000
```

Navigate to http://localhost:8000/ to view the web ui.

To update the web ui, navigate to the frontend directory, make changes and rebuild the ui.

## Capabilities

This demo focuses on the research assistant use case with some generalizations

- Skills: The agent is provided with a list of skills that it can leverage while attempting to address a user's query. Each skill is a python function that may be in any file in a folder made availabe to the agents. We separate the concept of global skills available to all agents `backend/global_utlis_dir` and user level skills `backend/files/user/<user_hash>/utils_dir`, relevant in a multi user environment. Agents are aware of a skill as they are appended to the system message

- Executable Keywords:

  - `@execute` : This app is designed such that code execution is an explicit request from the end user. For example, the agents are setup to not execute generated code by default. Rather, the user can respond with `@execute` to execute the most recent code block or make modifications.
  - `@memorize`: The app also supports an `@memorize` key word that runs a workflow where a new python skill is synthesized based on the recent conversation history. This is intended as an example of teachability where an agent can learn reusable skills.

## Acknowledgements

Based on the [AutoGen](https://microsoft.github.io/autogen) project.
Adapted in October 2023 from a research prototype (original credits: Gagan Bansal, Adam Fourney, Victor Dibia, Piali Choudhury, Saleema Amershi)
