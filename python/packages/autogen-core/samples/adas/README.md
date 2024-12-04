# User Guide for using ADAS in AutoGen

## Motivation

The Automated Design of Agentic Systems [paper](https://arxiv.org/pdf/2408.08435) introduces a way to automatically create powerful agentic system designs. This is motivated by the observation that in the field of machine learning, hand-designed solutions are often replaced by learned solutions over time.

We intend to implement this concept using the AutoGen framework, with the intention of discovering novel systems built directly with the AutoGen API.

## Background

### Summary

ADAS uses a meta-agent to generate creative and novel agent systems. Base agent systems (also known as building blocks) are defined entirely as code, which an LLM (powering the meta-agent) reads and interprets. The LLM then writes new code that defines a novel agent system, which can hopefully be more powerful at accomplishing the task at hand.

### Key Concepts

- **Agent System:** A software system designed to perform tasks autonomously. It can include one or more agents --which we will refer to as base agents-- and should be able to complete a task end-to-end (E2E), from receiving input, and producing a final output. Examples of an Agent System include “Chain-of-Thought" reasoning and planning, or “Self-Reflection”.
- **Building block:** A fundamental component or module that can be used to construct more complex systems. These building blocks are the basic units that can be combined and recombined in various ways to create different agentic systems. Effective building blocks include “Chain-of-Thought" reasoning and planning, or “Self-Reflection”.
- **Base agent:** The agent(s) within an Agent System that interact with each other using the event-based / messaging protocol as defined by AutoGen 0.4 API, and tries to accomplish the task as defined by the benchmark.
- **Foundation Models (FMs):** Used as modules within agentic systems for tasks requiring flexible reasoning and planning. Examples include GPT-3.5, GPT-4.o, Claude-Sonnet, Llama-70B, Gemini, etc.
- **Compound Agent System:** A complex system composed of multiple simpler agentic systems or building blocks. These individual components work together to perform more sophisticated tasks than they could individually. By combining building blocks, one can create a more powerful and versatile agentic system capable of handling a wide range of tasks and challenges.
- **Meta Agent Search:** An algorithm where a meta-agent iteratively programs new agents, tests their performance, and refines them based on an archive of previous discoveries.
- **Archive:** A file containing a list of 1) seed Agent Systems (Chain-of-Thought, Self-Reflection, etc.) which are manually defined, or 1) Agent Systems discovered by the meta-agent.
- **Meta Agent:** The agent that, given context of the benchmark and archive Agent Systems, tries to write code for novel Agent Systems.

### Methodology

- **Search Space:** Agents are defined in code, allowing the discovery of any possible agentic system.
- **Evaluation:** In the original ADAS paper, the meta-agent evaluates new agents on tasks across multiple domains, including coding, science, and math. We can adapt our code/dataset/evaluation to suit our purposes.

### Performance

In the original paper, the discovered agents significantly outperformed state-of-the-art hand-designed agents, demonstrating robustness and generality across domains.

To see the results of early experiments with ADAS in AutoGen, please see the Results section.

## ADAS in AutoGen

We have refactored the building block Agent Systems found in the original ADAS code to run using the AutoGen API. Specifically, we decided to implement these Agent Systems at the AutoGen-Core level of abstraction (rather than at the AutoGen-Agentchat level).

The vision for going down this path is that the meta-agent can design, using AutoGen-Core building blocks, a new (multi-)agent system, which if proven useful (after going through a period of testing/adoption by the team), be incorporated into the official AgentChat API.

See this document for more on the design tradeoffs between AutoGen-Core and AutoGen-Agentchat API.

### 4 manually crafted Agent Systems serving as the seeds to the archive
- More will be added over time

### Prompt to Meta-Agent

- Instructions: Generate novel code with name and thought of the new system
- Output and formatting requirements: Must be JSON, with `thought`, `name`, `code` (with the `forward` function)
- Examples of how to use or not use the AutoGen-Core API
    - Wrong ways to use the AutoGen-Core API
    - Correct ways to use the AutoGen-Core API
- Historical context (archive) of previous Agent Systems.
    - Documentation from official AutoGen website. Currently only parsing .md and .ipynb files from the [core-concepts](https://microsoft.github.io/autogen/dev/user-guide/core-user-guide/core-concepts/index.html) and [framework](https://microsoft.github.io/autogen/dev/user-guide/core-user-guide/framework/index.html) sections

### Meta-Agent does 5 iterations of LLM calls to create and edit code

- The original prompt contains all the instructions (generate novel code with name and thought of the new system), output and formatting requirements, examples of how to use or not use the API, and historical context (archive) of previous Agent Systems.
- 4 rounds of reflection:
    - Round 1 to reflect on interestingness, implementation mistakes, and improvement
    - Round 2 to revise based on the tips from the Wrong Implementation section in the original prompt
    - Round 3 to revise based on the tips of Correct Implementation
    - Round 4 to revise based on the tips from the official API documentation

### Meta-Agent will try again fresh if it encounters (code compilation) errors when trying to execute

An example of an exception is the following:
```
Error during evaluation:\nClosureAgent.register() takes 4 positional arguments but 5 positional arguments (and 1 keyword-only argument) were given\nCarefully consider where you went wrong in your latest implementation. Using insights from previous attempts, try to debug the current code to implement the same thought. Repeat your previous thought in 'thought', and put your thinking for debugging in 'debug_thought'", source='adas_agent')
```

Note: The `adas.py` script can still get stuck even if the code of the agent system compiles, but the agent system itself hangs due to a message being published to a topic that is not used. See this [section](#the-code-that-the-meta-agent-does-not-compile) under the Troubleshooting section for details on how to address this issue.

### Notable arguments to the script

Please see the `adas.py` file for details of all available settings.

- `data_filename`: the name of full path of the dataset location
- `benchmark_specific_utils_file`: Benchmark-specific utility file to load the dataset and also evaluate the outputs. This file must contain the load_dataset and compute_metrics functions
- `meta_agent_model_config`: JSON string of the AzureOpenAIChatCompletionClient settings for the Meta-Agent.
- `base_agent_model_config`: JSON string of the AzureOpenAIChatCompletionClient settings for the Base Agent.
- `n_generation`: number of generations of new agents that the meta-agent tries to discover
- `expr_name`: name of the output file containing both the original/seed and newly generated agent systems, as well as their fitness scores.
- `max_workers`: the number of threads to spin up in a ThreadPoolExecutor, to parallelize the execution of the particular Agent System that is currently being evaluated.

## QuickStart

### Install AutoGen-Core API

Follow the instructions here: [Installation — AutoGen](https://github.com/microsoft/autogen.git). Here is a summary:

```bash
python3 -m venv .venv
source .venv/bin/activate

# Install package at latest dev tag
pip install 'autogen-core==0.4.0.dev6'
# Or install in editable mode if you are modifying/testing AutoGen code at the same time
# git clone -b yeandy_adas https://github.com/yeandy/autogen.git
cd autogen/python
pip install -e packages/autogen-core
```

### Agent System code definitions
The ADAS framework will run E2E agent systems that are defined entirely inside a Python function. This function that encapsulates this logic is called `forward`, with two arguments `task` and `model_client_kwargs`. It looks like

```python
def forward(self, task, model_client_kwargs):
  # Agent logic
  result = model_client.create(task, ...)
  return result
```
The first argument is called `task` (represented as a string), which includes the prompt and input data. For example, the string could look like this:
```
You will be asked to read a passage and answer a question.

# Examples:
Passage: As of the census of 2000, there were 952 people, 392 households, and 241 families residing in the village. The population density was 952.9 people per square mile (367.6/km²). There were 449 housing units at an average density of 449.4 per square mile (173.4/km²). The racial makeup of the village was 96.11% White (U.S. Census), 0.95% African American (U.S. Census) or Race (United States Census), 0.11% Native American (U.S. Census), 0.11% Asian (U.S. Census), 0.21% from Race (United States Census), and 2.52% from two or more races. 1.05% of the population were Hispanics in the United States or Latino (U.S. Census) of any race.\nQuestion: How many more people, in terms of percentage, were from two or more races compared to being solely Native American or solely Asian?\nAnswer: 2.3

# Your Task
---
```

The second argument is called `model_client_kwargs` dictionary, which contains information about what type of LLM to use for the base agents. For example, it would look like this. To pass this information to the script, please see the following section on passing a JSON string of this information as a flag to the `adas.py` command.
```python
agent_model_kwargs =  {
    'api_version': '2024-08-01-preview',
    'azure_endpoint': 'https://<user>-aoai1.openai.azure.com/openai/deployments/gpt-35-turbo/chat/completions?api-version=2024-08-01-preview',
    'model_capabilities': {'function_calling': True, 'json_output': True, 'vision': True},
    'azure_ad_token_provider': 'DEFAULT',
    'model': 'gpt-35-turbo'
}
```
Finally, the output of this `forward` function should be the answer that the agent system comes up with.

There are several agent systems, along with their entire code inside the forward functions, already seeded in the archive. You can find this in the `adas_prompt.py` file.

#### Adding new agent systems (optional)
If you want to seed additional agent systems to the archive, follow the pattern used by the existing seed agent systems. Make sure to include name, thought, and code. Additionally, make sure to add the new system to the get_init_archive() function inside the adas.py file.

Note: If you add a new agent system after you’ve started generating new Agent Systems (next [section](#generate-new-agent-systems)), the meta-agent will not pick up this new seed agent system. This is because it will try to first detect the results file defined by the expr_name flag, and reference that file for the agent archive, instead of the `adas_prompt.py` file.

### Generate new Agent Systems
#### Prepare your dataset
First download your dataset locally.

Then create a copy the file called `utils_benchmark_template.py`, and name it with a suffix corresponding to your benchmark. For example, see `utils_drop.py`. Place this under the `adas` directory.

Under the `load_dataset` function, add logic to load in your dataset. Do any preprocessing that is required, such as adding instructions or any few-shot examples with the actual input data.

```python
# utils_my_benchmark.py
def load_dataset(filename: str) -> List[Dict[str, Any]]:
  df = pd.read_csv(filename)
  data = [{"inputs": "Your job is to solve this math problem: " + inputs, "targets": targets} for inputs, targets in df]
  return data
```
#### Prepare your evaluation function
In the same `utils_my_benchmark.py` file, add logic to the compute_metrics function to evaluate the ground truth against the predictions made by the agent system.

```python
# utils_my_benchmark.py
def compute_metrics(predictions: List[Any], labels: List[Any]) -> List[float]:
  return np.square(np.subtract(A, B)).mean()
```
### Choose the LLMs
#### Choose the LLMs for the meta-agent
Recommendation is GPT-4o, but you can choose whatever model you have access to on Azure.

o1-preview is also reported to be great at writing code, and we suggest you try that if you have access. Caveat: Beta version has [limitations](https://platform.openai.com/docs/guides/reasoning/beta-limitations#beta-limitations) such as not supporting `SystemMessages`.

This should be passed as a JSON string to the `meta_agent_model_config` flag.
```bash
--meta_agent_model_config='{"api_version": "2024-08-01-preview", "azure_endpoint": "https://andyye-aoai1.openai.azure.com/openai/deployments/o1-preview/chat/completions?api-version=2024-08-01-preview", "model_capabilities": {"function_calling": false, "json_output": false, "vision": false}, "azure_ad_token_provider": "DEFAULT", "model": "o1-preview-2024-09-12"}'
```
#### Choose the LLM for the base agents used within the agent system
The paper authors use GPT-3.5 (for cost purposes), but we recommend GPT-4o for better quality.

This should be passed as a JSON string to the `base_agent_model_config` flag.
```bash
--base_agent_model_config='{"api_version": "2023-03-15-preview", "azure_endpoint": "https://andyye-aoai1.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2023-03-15-preview", "model_capabilities": {"function_calling": true, "json_output": true, "vision": true}, "azure_ad_token_provider": "DEFAULT", "model": "gpt-4o-2024-08-06"}'
```
### Run ADAS
```bash
python packages/autogen-core/samples/adas/adas.py \
    --data_filename=/home/<user>/ADAS/dataset/drop_v0_dev.jsonl.gz \
    --n_generation=150 \
    --expr_name=drop_o1_preview_meta_gpt4o_base_results \
    --meta_agent_model_config='{"api_version": "2024-08-01-preview", "azure_endpoint": "https://<user>-aoai1.openai.azure.com/openai/deployments/o1-preview/chat/completions?api-version=2024-08-01-preview", "model_capabilities": {"function_calling": false, "json_output": false, "vision": false}, "azure_ad_token_provider": "DEFAULT", "model": " o1-preview-2024-09-12"}' \
    --base_agent_model_config='{"api_version": "2023-03-15-preview", "azure_endpoint": "https://<user>-aoai1.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2023-03-15-preview", "model_capabilities": {"function_calling": true, "json_output": true, "vision": true}, "azure_ad_token_pr ovider": "DEFAULT", "model": "gpt-4o-2024-08-06"}' \
    --benchmark_specific_utils_file='/home/<user>/autogen/python/packages/autogen-core/samples/adas/utils_drop.py'
```
You can increase the number of generations for the meta-agent to try creating. Note that if there is any compilation error, the count of the generation will be skipped. (Potential bug, or at least confusing behavior). You can also increase the number of threads to run evaluation of the agent system at any time.
```bash
python3 adas.py --n_generations 50 --max_workers 10
```
## Results for DROP benchmark
### Best Agent System that the Meta-Agent discovered
TODO

See this [section]() for the full list of discovered Agent Systems.

### Performance with different LLMs
The LLM that the Meta-Agent or the Base Agents use These are the results for the DROP benchmark
```
Meta-Agent | Base Agent
-----------|-----------
O1-preview | GPT4o
GPT3.5     | O1-preview
TODO       | TODO
TODO       | TODO
GPT4o      | TODO
TODO       | TODO
TODO       | TODO
```
## Troubleshooting
### Exceed token limit
If you are exceeding the token rate limit on your Azure AI Studio deployment

#### Increase the Rate Limit in Azure AI Studio
TODO: Insert image 

#### Setting the number of max_workers=1
This can be an argument passed to `adas.py`

#### Add sleep time after the forward function for each thread runs. Setting to 10 seconds is a good place to start 
```bash
adas.py --thread_sleep=10
```
### The code that the meta-agent does not compile
You may observe issues related to incorrect JSON or string formatting. This can occur after the meta-agent returns from querying any of its 5 prompts. For example:
```
Expecting ',' delimiter: line 5 column 11 (char 1626)
```
Or other errors you may see are “unterminated string literal”, etc. In this case, when trying to dynamically execute this code, the Meta-Agent will hit an exception and try the whole generation process again.

You shouldn’t need to do anything. Just note that since the meta-agent is starting over, it will prolong the time to generate a new Agent System. Additionally, the script will increment the `Generation` number. As a result, in the results file, you may see some generations being skipped. (This behavior can probably be altered to make more sense to the user)

### The code that the meta-agent does compile, but hangs during code execution 

The code for the Agent System compiles with no issue, but the systems hangs during execution of the AutoGen code. There are a few reasons and solutions.

#### Messages published to topics to which no Agents are subscribed 
```
INFO:autogen_core:Calling message handler for output_result with message type FinalAnswer published by coordinator_agent/default
ERROR:autogen_core:Error processing publish message
Traceback (most recent call last): File "/home/andyye/autogen/python/packages/autogen-core/src/autogen_core/application/_single_threaded_agent_runtime.py", line 372, in _process_publish agent = await self._get_agent(agent_id)
File "/home/andyye/autogen/python/packages/autogen-core/src/autogen_core/application/_single_threaded_agent_runtime.py", line 620, in _get_agent raise LookupError(f"Agent with name {agent_id.type} not found.")
LookupError: Agent with name output_result not found. 
```
The easiest solution is to terminate the program with `Ctrl + \` command, and then rerun the `adas.py` script. 

#### Certain Agent Systems will hang if `max_workers` is not equal to 1.

Another reason is if `max_workers` is not equal to 1. This means we spin up multiple threads to run the agent systems in parallel on the individual validation dataset. This has been overserved for the LLM_debate Agent System. The solution is to terminate the program, set `max_workers=1`, and rerun with this setting just for this agent system during its code execution / evaluation. You can then terminate after this has finished evaluating, and try again without `max_workers=1`.  

The reason for this is unknown. 

#### If you want to debug 
1. Copy the code that the meta-agent produces 
2. Put it in triple quotes: """def forward():\n	pass""", and print that string. 
3. Copy what is printed to console into a new file and try running it yourself to assist with debugging. 

### Event loop is closed 

If you see something like this during execution of the Agent System code, it should be fine. 
```
INFO:autogen_core:Calling message handler for reasoning_agent with message type Question published by Unknown
ERROR:asyncio:Task exception was never retrieved future: <Task finished name='Task-88' coro=<AsyncClient.aclose() done, defined at /home/andyye/autogen/python/.venv/lib/python3.10/site-packages/httpx/_client.py:2024> exception=RuntimeError('Event loop is closed')>
Traceback (most recent call last): File "/home/andyye/autogen/python/.venv/lib/python3.10/site-packages/httpx/_client.py", line 2031, in aclose await self._transport.aclose()
    File "/home/andyye/autogen/python/.venv/lib/python3.10/site-packages/httpx/_transports/default.py", line 389, in aclose await self._pool.aclose()
    File "/home/andyye/autogen/python/.venv/lib/python3.10/site-packages/httpcore/_async/connection_pool.py", line 313, in aclose await self._close_connections(closing_connections) File "/home/andyye/autogen/python/.venv/lib/python3.10/site-packages/httpcore/_async/connection_pool.py", line 305, in _close_connections await connection.aclose()
    File "/home/andyye/autogen/python/.venv/lib/python3.10/site-packages/httpcore/_async/connection.py", line 171, in aclose await self._connection.aclose()
    File "/home/andyye/autogen/python/.venv/lib/python3.10/site-packages/httpcore/_async/http11.py", line 265, in aclose await self._network_stream.aclose()
    File "/home/andyye/autogen/python/.venv/lib/python3.10/site-packages/httpcore/_backends/anyio.py", line 55, in aclose await self._stream.aclose()
    File "/home/andyye/autogen/python/.venv/lib/python3.10/site-packages/anyio/streams/tls.py", line 202, in aclose await self.transport_stream.aclose()
    File "/home/andyye/autogen/python/.venv/lib/python3.10/site-packages/anyio/_backends/_asyncio.py", line 1202, in aclose self._transport.close()
    File "/usr/lib/python3.10/asyncio/selector_events.py", line 706, in close self._loop.call_soon(self._call_connection_lost, None)
    File "/usr/lib/python3.10/asyncio/base_events.py", line 753, in call_soon self._check_closed()
    File "/usr/lib/python3.10/asyncio/base_events.py", line 515, in _check_closed raise RuntimeError('Event loop is closed')
RuntimeError: Event loop is closed INFO:autogen_core.events:{"prompt_tokens": 720, "completion_tokens": 104, "type": "LLMCall"}
INFO:autogen_core.events:{"prompt_tokens": 720, "completion_tokens": 149, "type": "LLMCall"} INFO:autogen_core.events:{"prompt_tokens": 720, "completion_tokens": 149, "type": "LLMCall"}
INFO:autogen_core.events:{"prompt_tokens": 720, "completion_tokens": 149, "type": "LLMCall"}
INFO:autogen_core.events:{"prompt_tokens": 720, "completion_tokens": 170, "type": "LLMCall"}
INFO:autogen_core:Publishing message of type Answer to all subscribers: {'content': 'To solve this problem, we need to carefully read the passage and identify the distances of the field goals mentioned in each quarter:\n\n1. Sebastian Janikowski got a 38-yard field goal.\n2. Jason Elam got a 23-yard field goal.\n3. Jason Elam got a 20-yard field goal.\n\nWe need to find out how many field goals of the game were longer than 40 yards. Only one field goal was longer than 40 yards, which was Sebastian Janikowski's 52-yard field goal attempt in overtime, but it didn't count because it was no good.\n\nTherefore, the number of field goals longer than 40 yards in the game is 0.\n\nSo the final answer is "0".'} INFO:autogen_core:Calling message handler for output_result with message type Answer published by reasoning_agent/default 
```

The thread still seems to finish with no issue and will still return an answer. 

The reason for this is unknown. 

## Ongoing work 

- Finish adding Quality-Diversity, Role_Assignment, and Take_A_Step_Back Agent Systems to the archive 
- Improve prompts to the meta-agent to reduce code errors 
- Add extra_create_args options such as `temperature`, `max_completion_tokens`, `top_p` in the model client `create()`. i.e. `extra_create_args={"temperature": 0.0}`

## Appendix

