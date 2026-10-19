# User Guide for using ADAS in AutoGen

TLDR:
This is a feature to use a meta-agent to generate new agent systems. For example, this agent system was discovered and written entirely by an agent using o1-preview:
```
def forward(self, task, model_client_kwargs):
    import asyncio
    import logging
    from dataclasses import dataclass
    from typing import List, Dict, Any
    from autogen_core import SingleThreadedAgentRuntime, default_subscription, RoutedAgent, message_handler, ClosureAgent, ClosureContext, TypeSubscription, DefaultTopicId
    from autogen_core.base import AgentId, AgentRuntime, MessageContext, TopicId
    from autogen_core.components.models import (
        ChatCompletionClient,
        SystemMessage,
        UserMessage,
        AssistantMessage,
        LLMMessage,
    )
    from autogen_ext.models import AzureOpenAIChatCompletionClient
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    from autogen_core.application.logging import TRACE_LOGGER_NAME

    # Configure logging as per documentation
    logging.basicConfig(level=logging.WARNING)
    logger = logging.getLogger(TRACE_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    token_provider = get_bearer_token_provider(DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default")

    # Create an AzureOpenAI model client.
    model_client = AzureOpenAIChatCompletionClient(
        model=model_client_kwargs["model"],
        api_version=model_client_kwargs["api_version"],
        azure_endpoint=model_client_kwargs["azure_endpoint"],
        azure_ad_token_provider=token_provider,
        model_capabilities={
            "vision": True,
            "function_calling": True,
            "json_output": True,
        },
    )

    @dataclass
    class Message:
        content: str

    @dataclass
    class FinalAnswer:
        answer: str

    @default_subscription
    class TreeOfThoughtsAgent(RoutedAgent):
        def __init__(self, model_client: ChatCompletionClient, max_depth: int = 3, beam_width: int = 3):
            super().__init__("TreeOfThoughtsAgent")
            self._model_client = model_client
            self._max_depth = max_depth
            self._beam_width = beam_width
            self._system_messages = [
                SystemMessage(
                    content="You are a helpful assistant who reasons step-by-step to solve complex problems.")
            ]

        async def generate_thoughts(self, prompt: List[LLMMessage], num_thoughts: int, cancellation_token) -> List[str]:
            # Generate multiple thoughts using the model
            thoughts = []
            # Create multiple async tasks to generate thoughts in parallel
            tasks = []
            for _ in range(num_thoughts):
                tasks.append(self._model_client.create(
                    prompt,
                    extra_create_args={"temperature": 1.0},
                    cancellation_token=cancellation_token,
                ))
            responses = await asyncio.gather(*tasks)
            for response in responses:
                thoughts.append(response.content.strip())
            return thoughts

        async def evaluate_thoughts(self, thoughts: List[str], ctx: MessageContext) -> List[Dict[str, Any]]:
            # Evaluate thoughts with the model outputting JSON-formatted scores
            eval_prompt = [
                SystemMessage(content="You are an assistant that evaluates reasoning steps for solving a problem."),
                UserMessage(
                    content=(
                        "Evaluate the following thoughts for their usefulness in solving the problem. "
                        "Provide a JSON array of objects with 'thought' and 'score' (from 1 to 10).\n\nThoughts:\n" + "\n".join(
                            [f"- {t}" for t in thoughts])
                    ),
                    source="user"
                )
            ]
            eval_response = await self._model_client.create(
                eval_prompt,
                cancellation_token=ctx.cancellation_token,
            )
            # Parse the JSON response
            import json
            try:
                evaluations = json.loads(eval_response.content.strip())
                # Each evaluation should be a dict with 'thought' and 'score'
                return evaluations
            except json.JSONDecodeError:
                # If parsing fails, assign default scores
                return [{"thought": t, "score": 5} for t in thoughts]

        @message_handler
        async def handle_message(self, message: Message, ctx: MessageContext) -> None:
            logger.info(f"Received task: {message.content}")
            initial_prompt = self._system_messages + [UserMessage(content=message.content, source="user")]
            tree = [[{"thought": "", "score": 0, "cumulative_score": 0}]]  # Initialize the tree with an empty path
            for depth in range(self._max_depth):
                new_branches = []
                logger.info(f"Depth {depth+1}")
                for path in tree:
                    # Build the prompt up to this point
                    prompt = initial_prompt.copy()
                    for node in path:
                        if node["thought"]:
                            prompt.append(AssistantMessage(content=node["thought"], source="assistant"))
                    # Generate thoughts
                    thoughts = await self.generate_thoughts(prompt, self._beam_width, ctx.cancellation_token)
                    logger.info(f"Generated thoughts: {thoughts}")
                    # Evaluate thoughts
                    evaluations = await self.evaluate_thoughts(thoughts, ctx)
                    logger.info(f"Evaluations: {evaluations}")
                    # Expand tree with evaluated thoughts
                    for eval in evaluations:
                        new_path = path + [{
                            "thought": eval["thought"],
                            "score": eval["score"],
                            "cumulative_score": path[-1]["cumulative_score"] + eval["score"]
                        }]
                        new_branches.append(new_path)
                # Select top-k paths based on cumulative_score
                if not new_branches:
                    logger.info("No more branches to expand.")
                    break  # No more thoughts to expand
                # Sort paths by cumulative score
                new_branches.sort(key=lambda p: p[-1]["cumulative_score"], reverse=True)
                tree = new_branches[:self._beam_width]
            # After reaching max depth, select the best path
            best_path = tree[0]
            final_answer = best_path[-1]["thought"]
            logger.info(f"Final answer: {final_answer}")
            # Publish the final answer to topic_id=TopicId(type="result", source="default")
            await self.publish_message(
                FinalAnswer(answer=final_answer),
                topic_id=TopicId(type="result", source="default")
            )

    # Main function
    async def main():
        # Create a queue to collect the final answer
        queue = asyncio.Queue()

        async def output_result(_agent: ClosureContext, message: FinalAnswer, ctx: MessageContext) -> None:
            await queue.put(message)

        # Initialize runtime
        runtime = SingleThreadedAgentRuntime()

        # Register TreeOfThoughtsAgent
        await TreeOfThoughtsAgent.register(
            runtime,
            "TreeOfThoughtsAgent",
            lambda: TreeOfThoughtsAgent(model_client)
        )

        # Register ClosureAgent
        result_topic = TypeSubscription(topic_type="result", agent_type="output_result")
        await ClosureAgent.register_closure(
            runtime,
            "output_result",
            output_result,
            subscriptions=lambda: [result_topic]
        )

        # Start the runtime
        runtime.start()

        # Publish initial message to TreeOfThoughtsAgent
        await runtime.publish_message(
            Message(content=task),
            topic_id=DefaultTopicId()
        )

        # Wait until idle
        await runtime.stop_when_idle()

        # Return the final answer
        final_message = await queue.get()
        return final_message.answer

    return asyncio.run(main())
```

## Motivation

The Automated Design of Agentic Systems (ADAS) [paper](https://arxiv.org/pdf/2408.08435) introduces a way to automatically create powerful agentic system designs. This is motivated by the observation that in the field of machine learning, hand-designed solutions are often replaced by learned solutions over time.

We have implemented this concept using the AutoGen framework, with the intention of discovering novel systems built directly with the AutoGen API.

## Background

### Summary

ADAS uses a meta-agent to generate creative and novel agent systems. Base agent systems (also known as building blocks) are defined entirely as code, which an LLM (powering the meta-agent) reads and interprets. The LLM then writes new code that defines a novel agent system, which can hopefully be more powerful at accomplishing the task at hand.

### Key Concepts

- **Agent System:** A software system designed to perform tasks autonomously. It can include one or more agents --which we will refer to as base agents-- and should be able to complete a task end-to-end (E2E), from receiving input, and producing a final output. Examples of an Agent System include "Chain-of-Thought" reasoning and planning, or "Self-Reflection".
- **Building block:** A fundamental component or module that can be used to construct more complex systems. These building blocks are the basic units that can be combined and recombined in various ways to create different agentic systems. Effective building blocks include "Chain-of-Thought" reasoning and planning, or "Self-Reflection".
- **Base agent:** The agent(s) within an Agent System that interact with each other using the event-based / messaging protocol as defined by AutoGen 0.4 API, and tries to accomplish the task as defined by the benchmark.
- **Foundation Models (FMs):** Used as modules within agentic systems for tasks requiring flexible reasoning and planning. Examples include GPT-3.5, GPT-4.o, Claude-Sonnet, Llama-70B, Gemini, etc.
- **Compound Agent System:** A complex system composed of multiple simpler agentic systems or building blocks. These individual components work together to perform more sophisticated tasks than they could individually. By combining building blocks, one can create a more powerful and versatile agentic system capable of handling a wide range of tasks and challenges.
- **Meta Agent Search:** An algorithm where a meta-agent iteratively programs new agents, tests their performance, and refines them based on an archive of previous discoveries.
- **Archive:** A list of 1) seed Agent Systems (Chain-of-Thought, Self-Reflection, etc.) which are manually defined, or 2) Agent Systems discovered by the meta-agent.
- **Meta Agent:** The agent that, given context of the benchmark and archive Agent Systems, tries to write code for novel Agent Systems.

### Methodology

- **Search Space:** Agents are defined in code, allowing the discovery of any possible agentic system.
- **Evaluation:** In the original ADAS paper, the meta-agent evaluates new agents on tasks across multiple domains, including coding, science, and math. We can adapt our code/dataset/evaluation to suit our purposes.

### Performance

In the original paper, the discovered agents significantly outperformed state-of-the-art hand-designed agents, demonstrating robustness and generality across domains.

To see the [results](#results-for-drop-benchmark) of early experiments with ADAS in AutoGen, please see the Results section.

## Implementing ADAS using AutoGen-Core API

We have refactored the building block Agent Systems found in the original ADAS code to run using the AutoGen API. Specifically, we decided to implement these Agent Systems at the `AutoGen-Core` level of abstraction (rather than at the `AutoGen-AgentChat` level). Here is why:

While it is generally the case that `AgentChat` makes it easier to put together an complex multi-agent system, as the API already has some preset teams that implements some of multi-agent design patterns (RoundRobinGroupChat, SelectorGroupChat), the `AgentChat` API has two main drawbacks 1) comprehensiveness and 2) low-level flexibility. 

On the comprehensiveness aspect, the Mixture of Agents design -– which is similar to chain-of-thought with self-consistency, where we aggregate the outputs of multiple agents –- is not a built-in team/orchestrator at the `AgentChat` level. As a result, this has to be implemented -- using the `AutoGen-Core` API -- into the codebase as an official team-level Agent, and also added as one of the seeds in the ADAS archive. This suggests that we don't even need to bother with `AutoGen-Agent-Chat` and just implement everything with the `AutoGen-Core` API.

On the low-level flexibility aspect, `AgentChat` hides a lot of flexibility on how to configure custom pub/sub topics, message handling, etc.

In other words, the abstraction at the `AgentChat` level, while useful in the short term for quick development, may restrict the ability for the meta-agent to design novel multi-agent patterns, which is really our goal. If all the meta-agent could do is build off the limited building blocks provided by `AgentChat`, then it wouldn't be able to be as creative as it could be. 

The ultimate vision for going down this path is that the meta-agent can design, using `AutoGen-Core` building blocks, a new (multi-)agent system, which if proven useful (after going through a period of testing/adoption by the team), be incorporated into the official `AgentChat` API.

## ADAS features in AutoGen

### 4 manually crafted Agent Systems serving as the seeds to the archive
- Please refer to the `get_init_archive()` function in the `adas_prompt.py` file for the current seed Agent Systems.
- More will be added over time

### Prompt to Meta-Agent

- Instructions: Generate novel code with name and thought of the new system
- Output and formatting requirements: Must be JSON, with `thought`, `name`, `code` (which must be written inside a `forward` function)
- Examples of how to use or not use the AutoGen-Core API
    - Wrong ways to use the AutoGen-Core API
    - Correct ways to use the AutoGen-Core API
- Historical context (archive) of previous Agent Systems.
- Documentation from official AutoGen website. Currently only parsing `.md` and `.ipynb` files from the [core-concepts](https://microsoft.github.io/autogen/dev/user-guide/core-user-guide/core-concepts/index.html) and [framework](https://microsoft.github.io/autogen/dev/user-guide/core-user-guide/framework/index.html) sections.

### Meta-Agent does 5 iterations of LLM calls to create and edit code

- The initial prompt to the meta-agent contains all the instructions (generate novel code with name and thought of the new system), output and formatting requirements, examples of how to use or not use the API, and historical context (archive) of previous Agent Systems.
- 4 rounds of reflection:
    - Round 1 to reflect on interestingness, implementation mistakes, and improvement
    - Round 2 to revise based on the tips from the "Wrong Implementation" section in the original prompt
    - Round 3 to revise based on the tips from the "Correct Implementation" section in the original prompt
    - Round 4 to revise based on the tips from the official API documentation

### Meta-Agent will try again fresh if it encounters (code compilation) errors when trying to execute

An example of an exception is the following:
```
Error during evaluation:\nClosureAgent.register() takes 4 positional arguments but 5 positional arguments (and 1 keyword-only argument) were given\nCarefully consider where you went wrong in your latest implementation. Using insights from previous attempts, try to debug the current code to implement the same thought. Repeat your previous thought in 'thought', and put your thinking for debugging in 'debug_thought'", source='adas_agent')
```
The current behavior is that the meta-agent will start over the generation sequence (using the 5 steps of LLM calls).

Note: The `adas.py` script can still get stuck even if the code of the agent system compiles. This can occur because the agent system itself hangs due to a message being published to a topic that is not used. See this [section](#the-code-that-the-meta-agent-does-not-compile) under the Troubleshooting section for details on how to address this issue.

### Notable arguments to the script

Please see the `adas.py` file for details of all available settings.

- `data_filename`: the name of full path of the dataset location
- `benchmark_specific_utils_file`: Benchmark-specific utility file to load the dataset and also evaluate the outputs. This file must contain the `load_dataset` and `compute_metrics` functions
- `meta_agent_model_config`: JSON string of the `AzureOpenAIChatCompletionClient` settings for the Meta-Agent.
- `base_agent_model_config`: JSON string of the `AzureOpenAIChatCompletionClient` settings for the Base Agent.
- `n_generation`: number of generations of new agents that the meta-agent tries to discover
- `expr_name`: name of the output file containing both the original/seed and newly generated agent systems, as well as their fitness scores.
- `save_dir`: the name of the directory to which the output file as indicated by `expr_name` will be saved.
- `max_workers`: the number of threads to spin up in a `ThreadPoolExecutor`, to parallelize the execution of the particular Agent System that is currently being evaluated.

## QuickStart

### Install AutoGen-Core API

Follow the instructions here: [Installation — AutoGen](https://github.com/microsoft/autogen.git). Here is a summary:

```bash
python3 -m venv .venv
source .venv/bin/activate

# Clone the ADAS repo to be able to use the DROP dataset for the sample.
# Recommended to perform a demo, though not required if you do not plan on evaluating with DROP, and intend to run with your own dataset / benchmark.
git clone https://github.com/ShengranHu/ADAS.git && cd ..

# Clone the AutoGen package, and switch to branch with the adas script.
git clone -b yeandy_adas https://github.com/yeandy/autogen.git
cd autogen/python

# Install autogen-core and autogen-ext in editable mode
pip install -e packages/autogen-core
pip install -e packages/autogen-ext
pip install -r samples/adas/requirements.txt
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
    'model': 'gpt-35-turbo',
    'azure_deployment': 'gpt-35-turbo'
}
```
Finally, the output of this `forward` function should be the answer that the agent system comes up with.

There are several agent systems, along with their entire code inside the forward functions, already seeded in the archive. You can find this in the `adas_prompt.py` file.

#### Adding new agent systems (optional)
If you want to seed additional agent systems to the archive, follow the pattern used by the existing seed agent systems. Make sure to include name, thought, and code. Additionally, make sure to add the new system to the get_init_archive() function inside the adas.py file.

Note: If you add a new agent system after you’ve started generating new Agent Systems (next [section](#generate-new-agent-systems)), the meta-agent will not pick up this new seed agent system. This is because it will try to first detect the results file defined by the expr_name flag, and reference that file for the agent archive, instead of the `adas_prompt.py` file.

### Generate new Agent Systems
#### Prepare your dataset
First download your dataset locally. It can be in any format, as long as your custom logic in the `load_dataset()` function properly reads the dataset file. 

Then create a copy the file called `utils_benchmark_template.py`, and name it with a suffix corresponding to your benchmark. For example, see `utils_drop.py`. Place this under the `adas` directory. This file will later be passed to the `benchmark_specific_utils_file` flag when running the script.

Under the `load_dataset` function, add logic to load in your dataset. Do any preprocessing that is required, such as adding instructions or any few-shot examples with the actual input data.

```python
# utils_my_benchmark.py
def load_dataset(file_path: str) -> List[Dict[str, Any]]:
  df = pd.read_csv(file_path)
  data = [{"inputs": "Your job is to solve this math problem: " + inputs, "targets": targets} for inputs, targets in df]
  return data
```
#### Prepare your evaluation function
In the same `utils_my_benchmark.py` file, add logic to the compute_metrics function to evaluate the ground truth against the predictions made by the agent system.

```python
# utils_my_benchmark.py
def compute_metrics(predictions: List[Any], labels: List[Any]) -> List[float]:
  return np.square(np.subtract(predictions, labels)).mean()
```
### Choose the LLMs
#### Choose the LLMs for the meta-agent
Recommendation is GPT-4o, but you can choose whatever model you have access to on Azure.

o1-preview is also reported to be great at writing code, and we suggest you try that if you have access. Caveat: Beta version has [limitations](https://platform.openai.com/docs/guides/reasoning/beta-limitations#beta-limitations) such as not supporting `SystemMessages`.

This should be passed as a JSON string to the `meta_agent_model_config` flag.
```bash
--meta_agent_model_config='{"api_version": "2024-08-01-preview", "azure_endpoint": "https://<user>-aoai1.openai.azure.com/openai/deployments/o1-preview/chat/completions?api-version=2024-08-01-preview", "model_capabilities": {"function_calling": false, "json_output": false, "vision": false}, "azure_ad_token_provider": "DEFAULT", "model": "o1-preview-2024-09-12", "azure_deployment": "o1-preview-2024-09-12"}'
```
#### Choose the LLM for the base agents used within the agent system
The paper authors use GPT-3.5 (for cost purposes), but we recommend GPT-4o for better quality.

This should be passed as a JSON string to the `base_agent_model_config` flag.
```bash
--base_agent_model_config='{"api_version": "2023-03-15-preview", "azure_endpoint": "https://<user>-aoai1.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2023-03-15-preview", "model_capabilities": {"function_calling": true, "json_output": true, "vision": true}, "azure_ad_token_provider": "DEFAULT", "model": "gpt-4o-2024-08-06", "azure_deployment": "gpt-4o-2024-08-06"}'
```
### Run ADAS
```bash
# For DROP benchmark
python samples/adas/adas.py \
    --data_filename=/home/<user>/ADAS/dataset/drop_v0_dev.jsonl.gz \
    --n_generation=150 \
    --expr_name=drop_o1_preview_meta_gpt4o_base_results \
    --save_dir='results/' \
    --max_workers=1 \
    --meta_agent_model_config='{"api_version": "2024-08-01-preview", "azure_endpoint": "https://<user>-aoai1.openai.azure.com/openai/deployments/o1-preview/chat/completions?api-version=2024-08-01-preview", "model_capabilities": {"function_calling": false, "json_output": false, "vision": false}, "azure_ad_token_provider": "DEFAULT", "model": " o1-preview-2024-09-12", "azure_deployment": "o1-preview-2024-09-12"}' \
    --base_agent_model_config='{"api_version": "2023-03-15-preview", "azure_endpoint": "https://<user>-aoai1.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2023-03-15-preview", "model_capabilities": {"function_calling": true, "json_output": true, "vision": true}, "azure_ad_token_provider": "DEFAULT", "model": "gpt-4o-2024-08-06", "azure_deployment": "gpt-4o-2024-08-06"}' \
    --benchmark_specific_utils_file='/home/<user>/autogen/python/samples/adas/utils_drop.py'

# For your own benchmark
python samples/adas/adas.py \
    --data_filename=/home/<user>/my_benchmark_data.csv \
    --n_generation=150 \
    --expr_name=drop_o1_preview_meta_gpt4o_base_results \
    --save_dir='results/' \
    --max_workers=1 \
    --meta_agent_model_config='{"api_version": "2024-08-01-preview", "azure_endpoint": "https://<user>-aoai1.openai.azure.com/openai/deployments/o1-preview/chat/completions?api-version=2024-08-01-preview", "model_capabilities": {"function_calling": false, "json_output": false, "vision": false}, "azure_ad_token_provider": "DEFAULT", "model": " o1-preview-2024-09-12", "azure_deployment": "o1-preview-2024-09-12"}' \
    --base_agent_model_config='{"api_version": "2023-03-15-preview", "azure_endpoint": "https://<user>-aoai1.openai.azure.com/openai/deployments/gpt-4o/chat/completions?api-version=2023-03-15-preview", "model_capabilities": {"function_calling": true, "json_output": true, "vision": true}, "azure_ad_token_provider": "DEFAULT", "model": "gpt-4o-2024-08-06", "azure_deployment": "gpt-4o-2024-08-06"}' \
    --benchmark_specific_utils_file='/home/<user>/autogen/python/samples/adas/utils_my_benchmark.py'
```
You can also increase the number of generations for the meta-agent to try creating. Note that if there is any compilation error, the count of the generation will be skipped. (Potential bug, or at least confusing behavior). 

You can also increase or decrease the number of threads to run evaluation of the agent system at any time. Note: There is currently some behavior (bug?) where if `max_workers` is not 1, the code hangs for certain systems. See this [section](#certain-agent-systems-will-hang-if-max_workers-is-not-equal-to-1) for details.
```bash
python3 adas.py --n_generations 100 --max_workers 1
```
## Results for DROP benchmark
### Best Agent System that the Meta-Agent discovered
See the files in the `adas/results` directory for the full list of discovered Agent Systems.
#### Meta-Agent used o1-preview, and Base Agents used GPT3.5
```
TODO: Testing/optimizations/reruns actively in progress.
See drop_o1_preview_meta_agent_gpt3.5_base_agent_results_run_archive.json for preliminary findings. 
```
#### Meta-Agent used o1-preview, and Base Agents used GPT4.0
```
TODO: Testing/optimizations/reruns actively in progress.
See drop_o1_preview_meta_agent_gpt4o_base_agent_results_run_archive.json for preliminary findings. 
```

### Performance with different LLMs
The LLM that the Meta-Agent or the Base Agents use These are the results for the DROP benchmark
| **Meta-Agent \ Base Agent** | **o1-preview** | **GPT-4o** | **GPT-3.5** |
|------------------------------|----------------|------------|-------------|
| **o1-preview**               |      TODO      |    TODO    |    TODO     |
| **GPT-4o**                   |      TODO      |    TODO    |    TODO     |

## Troubleshooting
### Exceed token limit
If you are exceeding the token rate limit on your Azure AI Studio deployment, try the following strategies.

#### Increase the Rate Limit in Azure AI Studio
Go to your deployment, and update the Tokens per Minute Rate Limit.
![Update GPT-3.5 deployment](./docs/azure_ai_studio_edit_deployment.png)


#### Setting the number of max_workers=1
This can be an argument passed to `adas.py`.

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
Traceback (most recent call last): File "/home/<user>/autogen/python/packages/autogen-core/src/autogen_core/application/_single_threaded_agent_runtime.py", line 372, in _process_publish agent = await self._get_agent(agent_id)
    File "/home/<user>/autogen/python/packages/autogen-core/src/autogen_core/application/_single_threaded_agent_runtime.py", line 620, in _get_agent raise LookupError(f"Agent with name {agent_id.type} not found.")
LookupError: Agent with name output_result not found. 
```
The easiest solution is to terminate the program with `Ctrl + \` command, and then rerun the `adas.py` script. 

#### Certain Agent Systems will hang if `max_workers` is not equal to 1.

Another reason is if `max_workers` is not equal to 1. This means we spin up multiple threads to run the agent systems in parallel on the individual validation dataset. This has been overserved for the `LLM_debate` or `Tree of Thought` Agent System. The solution is to terminate the program, set `max_workers=1`, and rerun with this setting just for this agent system during its code execution / evaluation. Unfortunately, this means longer time due to single thread of execution. You can then terminate after this has finished evaluating, and try again without `max_workers=1`.  

The reason for this is unknown. 

#### If you want to debug 
1. Copy the code that the meta-agent produces 
2. Put it in triple quotes: """def forward():\n	pass""", and print that string. 
3. Copy what is printed to console into a new file and try running it yourself to assist with debugging. 

### Event loop is closed 

If you see something like this during execution of the Agent System code, it should be fine. 
```
INFO:autogen_core:Calling message handler for reasoning_agent with message type Question published by Unknown
ERROR:asyncio:Task exception was never retrieved future: <Task finished name='Task-88' coro=<AsyncClient.aclose() done, defined at /home/<user>/autogen/python/.venv/lib/python3.10/site-packages/httpx/_client.py:2024> exception=RuntimeError('Event loop is closed')>
Traceback (most recent call last): File "/home/<user>/autogen/python/.venv/lib/python3.10/site-packages/httpx/_client.py", line 2031, in aclose await self._transport.aclose()
    File "/home/<user>/autogen/python/.venv/lib/python3.10/site-packages/httpx/_transports/default.py", line 389, in aclose await self._pool.aclose()
    File "/home/<user>/autogen/python/.venv/lib/python3.10/site-packages/httpcore/_async/connection_pool.py", line 313, in aclose await self._close_connections(closing_connections) File "/home/<user>/autogen/python/.venv/lib/python3.10/site-packages/httpcore/_async/connection_pool.py", line 305, in _close_connections await connection.aclose()
    File "/home/<user>/autogen/python/.venv/lib/python3.10/site-packages/httpcore/_async/connection.py", line 171, in aclose await self._connection.aclose()
    File "/home/<user>/autogen/python/.venv/lib/python3.10/site-packages/httpcore/_async/http11.py", line 265, in aclose await self._network_stream.aclose()
    File "/home/<user>/autogen/python/.venv/lib/python3.10/site-packages/httpcore/_backends/anyio.py", line 55, in aclose await self._stream.aclose()
    File "/home/<user>/autogen/python/.venv/lib/python3.10/site-packages/anyio/streams/tls.py", line 202, in aclose await self.transport_stream.aclose()
    File "/home/<user>/autogen/python/.venv/lib/python3.10/site-packages/anyio/_backends/_asyncio.py", line 1202, in aclose self._transport.close()
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
