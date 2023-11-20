# AutoGen Assistant

![ARA](./docs/ara_stockprices.png)

AutoGen Assistant is an Autogen-powered AI app (user interface) that can converse with you to help you conduct research, write and execute code, run saved skills, create new skills (explicitly and by demonstration), and adapt in response to your interactions.

### Capabilities / Roadmap

Some of the capabilities supported by the app frontend include the following:

- [x] Select fron a list of agents (current support for two agent workflows - `UserProxyAgent` and `AssistantAgent`)
- [x] Modify agent configuration (e.g. temperature, model, agent system message, model etc) and chat with updated agent configurations.
- [x] View agent messages and output files in the UI from agent runs.
- [ ] Support for more complex agent workflows (e.g. `GroupChat` workflows)
- [ ] Improved user experience (e.g., streaming intermediate model output, better summarization of agent responses, etc)

Project Structure:

- _autogenra/_ code for the backend classes and web api (FastAPI)
- _frontend/_ code for the webui, built with Gatsby and Tailwind

## Getting Started

AutoGen requires access to an LLM. Please see the [AutoGen docs](https://microsoft.github.io/autogen/docs/FAQ#set-your-api-endpoints) on how to configure access to your LLM provider. In this sample, We recommend setting up your `OPENAI_API_KEY` or `AZURE_OPENAI_API_KEY` environment variable and then specifying the exact model parameters to be used in the `llm_config` that is passed to each agent specification. See the `get_default_agent_config()` method in `utils.py` to see an example of setting up `llm_config`. The example below shows how to configure access to an Azure OPENAI LLM.

```python
llm_config = LLMConfig(
        config_list=[{
                "model": "gpt-4",
                "api_key": "<azure_api_key>",
                "api_base": "<azure api base>",
                "api_type": "azure",
                "api_version": "2023-06-01-preview"
        }],
        temperature=0,
    )
```

```bash
export OPENAI_API_KEY=<your_api_key>
```

### Install and Run

To install a prebuilt version of the app from PyPi. We highly recommend using a virtual environment (e.g. miniconda) and **python 3.10+** to avoid dependency conflicts.

```bash
pip install autogenra
autogenra ui --port 8081  # run the web ui on port 8081
```

### Install from Source

To install the app from source, clone the repository and install the dependencies.

```bash
pip install -e .
```

You will also need to build the app front end. Note that your Gatsby requires node > 14.15.0 . You may need to [upgrade your node](https://stackoverflow.com/questions/10075990/upgrading-node-js-to-latest-version) version as needed.

```bash
npm install --global yarn
cd frontend
yarn install
yarn build
```

The command above will build the frontend ui and copy the build artifacts to the `autogenra` web ui folder. Note that you may have to run `npm install  --force --legacy-peer-deps` to force resolve some peer dependencies.

Run the web ui:

```bash
autogenra ui --port 8081 # run the web ui on port 8081
```

Navigate to <http://localhost:8081/> to view the web ui.

To update the web ui, navigate to the frontend directory, make changes and rebuild the ui.

## Capabilities

This demo focuses on the research assistant use case with some generalizations:

- **Skills**: The agent is provided with a list of skills that it can leverage while attempting to address a user's query. Each skill is a python function that may be in any file in a folder made availabe to the agents. We separate the concept of global skills available to all agents `backend/files/global_utlis_dir` and user level skills `backend/files/user/<user_hash>/utils_dir`, relevant in a multi user environment. Agents are aware skills as they are appended to the system message. A list of example skills is available in the `backend/global_utlis_dir` folder. Modify the file or create a new file with a function in the same directory to create new global skills.

- **Conversation Persistence**: Conversation history is persisted in an sqlite database `database.sqlite`.

- **Default Agent Workflow**: The default a sample workflow with two agents - a user proxy agent and an assistant agent.

## Example Usage

Let us use a simple query demonstrating the capabilities of the research assistant.

```
Plot a chart of NVDA and TESLA stock price YTD. Save the result to a file named nvda_tesla.png
```

The agents responds by _writing and executing code_ to create a python program to generate the chart with the stock prices.

> Note than there could be multiple turns between the `AssistantAgent` and the `UserProxyAgent` to produce and execute the code in order to complete the task.

![ARA](./docs/ara_stockprices.png)

> Note: You can also view the debug console that generates useful information to see how the agents are interacting in the background.

<!-- ![ARA](./docs/ara_console.png) -->

## FAQ

- How do I add more skills to the research assistant? This can be done by adding a new file with documented functions to `autogenra/web/skills/global` directory.
- How do I specify the agent configuration (e.g. temperature, model, agent system message, model etc). You can do either from the UI interface or by modifying the default agent configuration in `utils.py` (`get_default_agent_config()` method)
- How do I reset the conversation? You can reset the conversation by deleting the `database.sqlite` file. You can also delete user files by deleting the `autogenra/web/files/user/<user_id_md5hash>` folder.
- How do I view messages generated by agents? You can view the messages generated by the agents in the debug console. You can also view the messages in the `database.sqlite` file.

## Acknowledgements

Based on the [AutoGen](https://microsoft.github.io/autogen) project.
Adapted in October 2023 from a research prototype (original credits: Gagan Bansal, Adam Fourney, Victor Dibia, Piali Choudhury, Saleema Amershi, Ahmed Awadallah, Chi Wang)
