---
title: Preventative Healthcare with AutoGen
emoji: 🔥
colorFrom: yellow
colorTo: purple
sdk: streamlit
sdk_version: 1.45.1
app_file: app.py
pinned: false
short_description: Using AI agents for preventative healthcare maintenance
---
[//]: <Add samples here https://github.com/microsoft/autogen/tree/main/python/samples> 

## AutoGen Multi-Agent Chat Preventative Healthcare

This is a multi-agent system built on top of [AutoGen](https://github.com/microsoft/autogen) agents designed to automate and optimize preventative healthcare outreach. It uses multiple agents, large language models (LLMs) and asynchronous programming to streamline the process of identifying patients who meet specific screening criteria and generating personalized outreach emails. 

The system uses an OpenAI-compatible API key and model endpoints with the inference service called [Intel® AI for Enterprise Inference](https://github.com/opea-project/Enterprise-Inference), powered by Intel® Gaudi® AI accelerators.

Credit: Though heavily modified, the original idea comes from Mike Lynch on his [Medium blog](https://medium.com/@micklynch_6905/hospitalgpt-managing-a-patient-population-with-autogen-powered-by-gpt-4-mixtral-8x7b-ef9f54f275f1). 

## Workflow:

<p align="center">
  <img width="700" src="images/prev_healthcare_4.drawio.svg">
</p>

1. **Define screening criteria**: After getting the general screening task from the user, the User Proxy Agent starts a conversation between the Epidemiologist Agent and the Doctor Critic Agent to define the criteria for patient outreach based on the target screening type. The output criteria is age range (e.g., 40–70), gender, and relevant medical history.

2. **Select and identify patients based on the screening criteria**: The Data Analyst Agent filters patient data from a CSV file based on the defined criteria, including age range, gender, and medical conditions. The patient data were synthetically generated. You can find the sample data under [data/patients.csv](data/patients.csv).

3. **Generate outreach emails**: The program generates outreach emails for the filtered patients using LLMs and saves them as text files. 

## Setup
If you want to host the application on Hugging Face Spaces, the easiest way is to duplicate the Hugging Face Space, and set up your own API secrets as detailed further below.

If you want a local copy of the application to run, you can clone the repository and then navigate into the folder with:

```bash
git clone https://huggingface.co/spaces/Intel/preventative_healthcare
cd preventative_healthcare
```

You can use the `uv` package to manage your virtual environment and dependencies. Just initialize the `uv` project:

```bash
uv init --bare
```

Install dependencies:
```bash
uv add -r requirements.txt
```


### OpenAI API Key, Model Name, and Endpoint URL

1. If using the Hugging Face Spaces app, you can add your OpenAI-compatible API key and the model endpoint URL to the Hugging Face Settings under "Variables and secrets". They are called by a function called `st.secrets` [here in the app.py code](https://huggingface.co/spaces/Intel/preventative_healthcare/blob/main/app.py#L295). 

2. If deploying a local version with Streamlit frontend, you can add your details to a file under `.streamlit/secrets.toml` that looks like this:
```bash
OPENAI_API_KEY = "your-api-key"
OPENAI_BASE_URL = "https://api.inference.denvrdata.com/v1/"
```
3. Finally, if you just want to use the Python script without any front-end interface, you can just add your API key to the [OAI_CONFIG_LIST.json](https://huggingface.co/spaces/Intel/preventative_healthcare/blob/main/OAI_CONFIG_LIST.json) file. Just don't expose your precious API key to the world! You can modify the `api_key`, `model` and `base_url` to the model name and endpoint URL that you are using. This file should look like:
```json
[
    {
        "model": "meta-llama/Llama-3.3-70B-Instruct",
        "base_url": "https://api.inference.denvrdata.com/v1/",
        "api_key": "openai_key",
        "price": [0.0, 0.0]
    },
    {
        "model": "deepseek-ai/DeepSeek-R1-Distill-Llama-70B",
        "base_url": "https://api.inference.denvrdata.com/v1/",
        "api_key": "openai_key",
        "price": [0.0, 0.0]
    }
]
```

### Modifying prompts
To modify prompts, you can edit them in the UI on the left sidebar, or you can edit them in the following files:

1. User proxy agent: the agent responsible for passing along the user's preventative healthcare task to the other agents.
[prompts/user_proxy_prompt.py](prompts/user_proxy_prompt.py)
2. Epidemiologist agent: The disease specialist agent who will gather the preventative healthcare task and decide on patient criteria.
[prompts/epidemiologist_prompt.py](prompts/outreach_email_prompt.py)
3. Doctor Critic agent: The doctor critic agent reviews the criteria from the epidemiologist and passes this along. The output will be used to filter actual patients from the patient data.
[prompts/doctor_critic_prompt.py](prompts/doctor_critic_prompt.py)
4. Outreach email: This is not an agent, but still uses an LLM to build the outreach email. 
[prompts/outreach_email_prompt.py](prompts/outreach_email_prompt.py)

### Example Usage

If you want to run the app with streamlit, you can run it locally with:

```bash
uv run streamlit run app.py
```

If you want to just run just the Python script without any frontend interface, you can use the following command with arguments as below:

```bash
python intelpreventativehealthcare.py \
    --oai_config "OAI_CONFIG_LIST.json" \
    --target_screening "Type 2 Diabetes" \
    --patients_file "data/patients.csv" \
    --phone "123-456-7890" \
    --email "doctor@doctor.com" \
    --name "Benjamin Consolvo"
```

The arguments are defined as follows:

- `--oai_config`: Path to the `OAI_CONFIG_LIST.json` file, which contains the model endpoints, model name, and api key.
- `--target_screening`: The type of screening task (e.g., "Type 2 Diabetes screening").
- `--patients_file`: Path to the CSV file containing patient data. Default is `data/patients.csv`.
- `--phone`: Phone number to include in the outreach emails. Default is `123-456-7890`.
- `--email`: Reply email address to include in the outreach emails. Default is `doctor@doctor.com`.
- `--name`: Name to include in the outreach emails. Default is `Benjamin Consolvo`.

The output emails will be saved as text files in the `data/` directory.

### 6 Lessons Learned

Here are some lessons learned while building this preventative healthcare agentic application:

1. Some LLMs perform better than others at certain tasks. While this may seem obvious, in practice, you often need to adjust which LLMs you use after seeing the results. For example, the [meta-llama/Llama-3.3-70B-Instruct](https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct) model was much more consistent and hallucinated less than [mistralai/Mixtral-8x7B-v0.1](https://huggingface.co/mistralai/Mixtral-8x7B-v0.1) for email generation.
2. Setting temperature to 0 is important for getting a consistent output response from LLMs.  
3. Prompt engineering is very important in the age of instructing LLMs on what to do.
    - Be specific and detailed
    - Give exact output format examples
    - Tell the LLM what to do, rather than telling it everything it should not do
You can read more about prompt engineering on [OpenAI's blog here](https://help.openai.com/en/articles/6654000-best-practices-for-prompt-engineering-with-the-openai-api)

4. Certain tasks are easier to manage with traditional programming rather than building an agent to do it. In the case of getting data consistently from a database with a specified format, write a function rather than building an agent. The LLM may hallucinate and not carry out the task correctly. There is a function built in the code here called [get_patients_from_criteria](intelpreventativehealthcare.py#L150) that filters patient data from a CSV file based on specified criteria. LLMs can hallucinate and invent data that are not a part of the database, even when given specific instructions to only use data from the database! You will need to assess when to tell the agent when to use specific tools.
5. Do operations asynchronously wherever possible. Instead of writing emails one by one in a for loop, write them all at once with `async`. 
6. Code writing tools like GitHub Copilot, Cursor, and Windsurf can save a lot of time, but you still need to pay attention to the output and understand what is going on with the code. A lot of unecessary lines of code and technical debt will be accumulated by relying purely on code generation tools.

## Follow Up

Connect to LLMs on Intel Gaudi AI accelerators with just an endpoint and an OpenAI-compatible API key, using the inference endpoint [Intel® AI for Enterprise Inference](https://github.com/opea-project/Enterprise-Inference), powered by OPEA. At the time of writing, the endpoint is available on cloud provider [Denvr Dataworks](https://www.denvrdata.com/intel). 

Chat with 6K+ fellow developers on the [Intel DevHub Discord](https://discord.gg/kfJ3NKEw5t).

Follow [Intel Software on LinkedIn](https://www.linkedin.com/showcase/intel-software/).

For more Intel AI developer resources, see [developer.intel.com/ai](https://developer.intel.com/ai).
