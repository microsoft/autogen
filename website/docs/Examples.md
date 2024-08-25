# Examples

## Automated Multi Agent Chat

AutoGen offers conversable agents powered by LLM, tool or human, which can be used to perform tasks collectively via automated chat. This framework allows tool use and human participation via multi-agent conversation.
Please find documentation about this feature [here](/docs/Use-Cases/agent_chat).

Links to notebook examples:

### Code Generation, Execution, and Debugging

- Automated Task Solving with Code Generation, Execution & Debugging - [View Notebook](/docs/notebooks/agentchat_auto_feedback_from_code_execution)
- Automated Code Generation and Question Answering with Retrieval Augmented Agents - [View Notebook](/docs/notebooks/agentchat_RetrieveChat)
- Automated Code Generation and Question Answering with [Qdrant](https://qdrant.tech/) based Retrieval Augmented Agents - [View Notebook](/docs/notebooks/agentchat_RetrieveChat_qdrant)

### Multi-Agent Collaboration (>3 Agents)

- Automated Task Solving by Group Chat (with 3 group member agents and 1 manager agent) - [View Notebook](/docs/notebooks/agentchat_groupchat)
- Automated Data Visualization by Group Chat (with 3 group member agents and 1 manager agent) - [View Notebook](/docs/notebooks/agentchat_groupchat_vis)
- Automated Complex Task Solving by Group Chat (with 6 group member agents and 1 manager agent) - [View Notebook](/docs/notebooks/agentchat_groupchat_research)
- Automated Task Solving with Coding & Planning Agents - [View Notebook](/docs/notebooks/agentchat_planning)
- Automated Task Solving with transition paths specified in a graph - [View Notebook](/docs/notebooks/agentchat_groupchat_finite_state_machine)
- Running a group chat as an inner-monolgue via the SocietyOfMindAgent - [View Notebook](/docs/notebooks/agentchat_society_of_mind)
- Running a group chat with custom speaker selection function - [View Notebook](/docs/notebooks/agentchat_groupchat_customized)

### Sequential Multi-Agent Chats

- Solving Multiple Tasks in a Sequence of Chats Initiated by a Single Agent - [View Notebook](/docs/notebooks/agentchat_multi_task_chats)
- Async-solving Multiple Tasks in a Sequence of Chats Initiated by a Single Agent - [View Notebook](/docs/notebooks/agentchat_multi_task_async_chats)
- Solving Multiple Tasks in a Sequence of Chats Initiated by Different Agents - [View Notebook](/docs/notebooks/agentchats_sequential_chats)

### Nested Chats

- Solving Complex Tasks with Nested Chats - [View Notebook](/docs/notebooks/agentchat_nestedchat)
- Solving Complex Tasks with A Sequence of Nested Chats - [View Notebook](/docs/notebooks/agentchat_nested_sequential_chats)
- OptiGuide for Solving a Supply Chain Optimization Problem with Nested Chats with a Coding Agent and a Safeguard Agent - [View Notebook](/docs/notebooks/agentchat_nestedchat_optiguide)
- Conversational Chess with Nested Chats and Tool Use - [View Notebook](/docs/notebooks/agentchat_nested_chats_chess)

### Applications

- Automated Continual Learning from New Data - [View Notebook](/docs/notebooks/agentchat_stream)
<!-- - [OptiGuide](https://github.com/microsoft/optiguide) - Coding, Tool Using, Safeguarding & Question Answering for Supply Chain Optimization -->
- [AutoAnny](https://github.com/autogen-ai/autogen/tree/main/samples/apps/auto-anny) - A Discord bot built using AutoGen

### Tool Use

- **Web Search**: Solve Tasks Requiring Web Info - [View Notebook](/docs/notebooks/agentchat_web_info)
- Use Provided Tools as Functions - [View Notebook](/docs/notebooks/agentchat_function_call_currency_calculator)
- Use Tools via Sync and Async Function Calling - [View Notebook](/docs/notebooks/agentchat_function_call_async)
- Task Solving with Langchain Provided Tools as Functions - [View Notebook](/docs/notebooks/agentchat_langchain)
- **RAG**: Group Chat with Retrieval Augmented Generation (with 5 group member agents and 1 manager agent) - [View Notebook](/docs/notebooks/agentchat_groupchat_RAG)
- Function Inception: Enable AutoGen agents to update/remove functions during conversations. - [View Notebook](/docs/notebooks/agentchat_inception_function)
- Agent Chat with Whisper - [View Notebook](/docs/notebooks/agentchat_video_transcript_translate_with_whisper)
- Constrained Responses via Guidance - [View Notebook](/docs/notebooks/agentchat_guidance)
- Browse the Web with Agents - [View Notebook](/docs/notebooks/agentchat_surfer)
- **SQL**: Natural Language Text to SQL Query using the [Spider](https://yale-lily.github.io/spider) Text-to-SQL Benchmark - [View Notebook](/docs/notebooks/agentchat_sql_spider)
- **Web Scraping**: Web Scraping with Apify - [View Notebook](/docs/notebooks/agentchat_webscraping_with_apify)
- **Write a software app, task by task, with specially designed functions.** - [View Notebook](/docs/notebooks/agentchat_function_call_code_writing).

### Human Involvement

- Simple example in ChatGPT style [View example](https://github.com/autogen-ai/autogen/blob/main/samples/simple_chat.py)
- Auto Code Generation, Execution, Debugging and **Human Feedback** - [View Notebook](/docs/notebooks/agentchat_human_feedback)
- Automated Task Solving with GPT-4 + **Multiple Human Users** - [View Notebook](/docs/notebooks/agentchat_two_users)
- Agent Chat with **Async Human Inputs** - [View Notebook](/docs/notebooks/async_human_input)

### Agent Teaching and Learning

- Teach Agents New Skills & Reuse via Automated Chat - [View Notebook](/docs/notebooks/agentchat_teaching)
- Teach Agents New Facts, User Preferences and Skills Beyond Coding - [View Notebook](/docs/notebooks/agentchat_teachability)
- Teach OpenAI Assistants Through GPTAssistantAgent - [View Notebook](/docs/notebooks/agentchat_teachable_oai_assistants)
- Agent Optimizer: Train Agents in an Agentic Way - [View Notebook](/docs/notebooks/agentchat_agentoptimizer)

### Multi-Agent Chat with OpenAI Assistants in the loop

- Hello-World Chat with OpenAi Assistant in AutoGen - [View Notebook](/docs/notebooks/agentchat_oai_assistant_twoagents_basic)
- Chat with OpenAI Assistant using Function Call - [View Notebook](/docs/notebooks/agentchat_oai_assistant_function_call)
- Chat with OpenAI Assistant with Code Interpreter - [View Notebook](/docs/notebooks/agentchat_oai_code_interpreter)
- Chat with OpenAI Assistant with Retrieval Augmentation - [View Notebook](/docs/notebooks/agentchat_oai_assistant_retrieval)
- OpenAI Assistant in a Group Chat - [View Notebook](/docs/notebooks/agentchat_oai_assistant_groupchat)
- GPTAssistantAgent based Multi-Agent Tool Use - [View Notebook](/docs/notebooks/gpt_assistant_agent_function_call)

### Non-OpenAI Models
- Conversational Chess using non-OpenAI Models - [View Notebook](/docs/notebooks/agentchat_nested_chats_chess_altmodels)

### Multimodal Agent

- Multimodal Agent Chat with DALLE and GPT-4V - [View Notebook](/docs/notebooks/agentchat_dalle_and_gpt4v)
- Multimodal Agent Chat with Llava - [View Notebook](/docs/notebooks/agentchat_lmm_llava)
- Multimodal Agent Chat with GPT-4V - [View Notebook](/docs/notebooks/agentchat_lmm_gpt-4v)

### Long Context Handling

<!-- - Conversations with Chat History Compression Enabled - [View Notebook](https://github.com/autogen-ai/autogen/blob/main/notebook/agentchat_compression.ipynb) -->
- Long Context Handling as A Capability - [View Notebook](/docs/notebooks/agentchat_transform_messages)

### Evaluation and Assessment

- AgentEval: A Multi-Agent System for Assess Utility of LLM-powered Applications - [View Notebook](/docs/notebooks/agenteval_cq_math)

### Automatic Agent Building

- Automatically Build Multi-agent System with AgentBuilder - [View Notebook](/docs/notebooks/autobuild_basic)
- Automatically Build Multi-agent System from Agent Library - [View Notebook](/docs/notebooks/autobuild_agent_library)

### Observability
- Track LLM calls, tool usage, actions and errors using AgentOps - [View Notebook](/docs/notebooks/agentchat_agentops)
- Cost Calculation - [View Notebook](/docs/notebooks/agentchat_cost_token_tracking)

## Enhanced Inferences

### Utilities

- API Unification - [View Documentation with Code Example](https://autogen-ai.github.io/autogen/docs/Use-Cases/enhanced_inference/#api-unification)
- Utility Functions to Help Managing API configurations effectively - [View Notebook](/docs/topics/llm_configuration)

### Inference Hyperparameters Tuning

AutoGen offers a cost-effective hyperparameter optimization technique [EcoOptiGen](https://arxiv.org/abs/2303.04673) for tuning Large Language Models. The research study finds that tuning hyperparameters can significantly improve the utility of them.
Please find documentation about this feature [here](/docs/Use-Cases/enhanced_inference).

Links to notebook examples:
* [Optimize for Code Generation](https://github.com/autogen-ai/autogen/blob/main/notebook/oai_completion.ipynb) | [Open in colab](https://colab.research.google.com/github/autogen-ai/autogen/blob/main/notebook/oai_completion.ipynb)
* [Optimize for Math](https://github.com/autogen-ai/autogen/blob/main/notebook/oai_chatgpt_gpt4.ipynb) | [Open in colab](https://colab.research.google.com/github/autogen-ai/autogen/blob/main/notebook/oai_chatgpt_gpt4.ipynb)
