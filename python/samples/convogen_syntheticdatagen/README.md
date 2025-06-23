# ConvoGen: Enhancing Conversational AI with Synthetic Data: A Multi-Agent Approach
This repository contains necessary scripts to generate conversations using ConvoGen

<div align="center">
  <a href="https://arxiv.org/abs/2503.17460"><img src="https://img.shields.io/badge/Paper-arXiv-red";" alt="arXiv"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/Code%20License-MIT-blue" alt="Code License"></a>
</div>

## Introduction

In this paper, we present **ConvoGen**: an innovative framework for generating synthetic conversational data using multi-agent systems. Our method leverages few-shot learning and introduces iterative sampling from a dynamically updated few-shot hub to create diverse and realistic conversational scenarios. The generated data has numerous applications, including training and evaluating conversational AI models, and augmenting existing datasets for tasks like conversational intent classification or conversation summarization. Our experiments demonstrate the effectiveness of this method in producing high-quality diverse synthetic conversational data, highlighting its potential to enhance the development and evaluation of conversational AI systems.

![Multi-Agents](assets/multi-agents.png)

We utilize the AutoGen framework for creating the group chat between the multiple agents based on a generated experience. The experience represents a situation that gathers a group of personas with generated relations, a topic, and conversation starter. First, each individual's persona is used to configure a corresponding agent using a system message, a name and a description. In addition to the persona definition, the system message includes additional guidelines for the agent on how to drive the conversation. Next, the conversation is instantiated by a user proxy who sends a message to the group chat manager composed of the situation, the relations between the individuals, the topic, and the conversation starter. The group chat manager then uses the predefined speaker selection prompt to select the next speaker from the list of agents based on the current conversation context and the agents' descriptions. The speaker responds to the group chat manager which hence broadcasts the message to all the other individuals in the group, and selects the next speaker to proceed. This process continues until a maximum number of turns is reached.

![Persona IDs Slide](assets/PersonaIDsSlide.png)

## Prerequisites
Using Conda is recommended, first create a conda environment
```bash
conda install -n convogen python==3.10.11
conda activate convogen
```
Install the requirements within the conda env
```
pip install -r requirements.txt
```

## Usage

Under `llm/models/settings`, create a .env file to add your LLM Endpoint. In our experiments, we were using AzureOpenAI with GPT-4O
```
AZURE_OPENAI_ENDPOINT=<Azure OpenAI Endpoint>
AZURE_OPENAI_API_VERSION=<Azure OpenAI API Version>
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME=<Azure OpenAI Deployment Name>
```

### Define your own prompt and shots for situation generation
In case of automatically generated personas, refer to the prompt in [llm/prompts/situations/prompt-v1.md](llm/prompts/situations/prompt-v1.md) and the corresponding shot in [llm/prompts/situations/shots/shot-1.json](llm/prompts/situations/shots/shot-1.json)

In case of predefined personas, refer to the prompt in [llm/prompts/situations/prompt-persona-v1.md](llm/prompts/situations/prompt-persona-v1.md) and the corresponding shot in [llm/prompts/situations/shots-personas/shot-1.json](llm/prompts/situations/shots-personas/shot-1.json)

Next you need to define a prompt configuration that points to your prompt path , shot path, and defines the shot selection method [fixed](llm/promptConfigs/situations-fixed-shots-1.yaml) or [random](llm/promptConfigs/situations-random-shots-1.yaml) and the number of shots to utilize in the prompt as well as the number of situations to generate for each call to the endpoint.

### Generate situations
To start generating conversations using ConvoGen using auto Generated personas:
1. Write your config file similar to configs/gen-config-1.yaml
2. Run the following command:
```
python main.py -c configs/gen-config-1.yaml
```

To start generating conversations using pre-defined personas
1. Create a personas jsonl file similar to [llm/prompts/personas/personahub-placeholder.jsonl](llm/prompts/personas/personahub-placeholder.jsonl). you can find a good source of personas to use in [PersonaHub](https://huggingface.co/datasets/proj-persona/PersonaHub)
2. Write your config similar to configs/gen-config-persona-1.yaml
3. Run the following command:
```
python main.py -c configs/gen-config-persona-1.yaml
```

### Upload Data to Azure Blob (Optional)

To upload a set of experiences (situations) to an azure blob storage
1. Write your config file similar to configs/upload-data-1.yaml
2. Run the following command:
```
python compile_situations_dataset.py -c configs/upload-data-1.yaml
```

## Effective Use and Ethical Considerations for ConvoGen

- Operational factors for ConvoGen include selecting appropriate language models

- We strongly recommend users apply Responsible AI (RAI) safety filters when using ConvoGen to ensure the generated conversations align with ethical standards and avoid unintended or harmful results. These filters can help detect and mitigate potential risks related to biases, safety, and compliance. 


## Citation

If you find our work helpful, please consider citing it:
```
@misc{gody2025,
    title={ConvoGen: Enhancing Conversational AI with Synthetic Data: A Multi-Agent Approach},
    author={Reem Gody, Mahmoud Goudy, Ahmed Y Tawfik},
    year={2025},
    eprint={},
    archivePrefix={arXiv},
    primaryClass={cs.CL}
}
```

## Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft 
trademarks or logos is subject to and must follow 
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.
