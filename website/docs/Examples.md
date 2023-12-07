# Examples

### Automated Multi Agent Chat

AutoGen offers conversable agents powered by LLM, tool or human, which can be used to perform tasks collectively via automated chat. This framework allows tool use and human participation via multi-agent conversation.
Please find documentation about this feature [here](/docs/Use-Cases/agent_chat).

Links to notebook examples:


1. **Code Generation, Execution, and Debugging**

   - Automated Task Solving with Code Generation, Execution & Debugging - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_auto_feedback_from_code_execution.ipynb)
   - Auto Code Generation, Execution, Debugging and Human Feedback - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_human_feedback.ipynb)
   - Automated Code Generation and Question Answering with Retrieval Augmented Agents - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_RetrieveChat.ipynb)
   - Automated Code Generation and Question Answering with [Qdrant](https://qdrant.tech/) based Retrieval Augmented Agents - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_qdrant_RetrieveChat.ipynb)

2. **Multi-Agent Collaboration (>3 Agents)**

   - Automated Task Solving with GPT-4 + Multiple Human Users - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_two_users.ipynb)
   - Automated Task Solving by Group Chat (with 3 group member agents and 1 manager agent) - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_groupchat.ipynb)
   - Automated Data Visualization by Group Chat (with 3 group member agents and 1 manager agent) - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_groupchat_vis.ipynb)
   - Automated Complex Task Solving by Group Chat (with 6 group member agents and 1 manager agent) - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_groupchat_research.ipynb)
   - Automated Task Solving with Coding & Planning Agents - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_planning.ipynb)
   - Automated Task Solving with agents divided into 2 groups - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_hierarchy_flow_using_select_speaker.ipynb)
   - Automated Task Solving with transition paths specified in a graph - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_graph_modelling_language_using_select_speaker.ipynb)

3. **Applications**

   - Automated Chess Game Playing & Chitchatting by GPT-4 Agents - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_chess.ipynb)
   - Automated Continual Learning from New Data - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_stream.ipynb)
   - [OptiGuide](https://github.com/microsoft/optiguide) - Coding, Tool Using, Safeguarding & Question Anwering for Supply Chain Optimization

4. **Tool Use**

   - **Web Search**: Solve Tasks Requiring Web Info - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_web_info.ipynb)
   - Use Provided Tools as Functions - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_function_call.ipynb)
   - Task Solving with Langchain Provided Tools as Functions - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_langchain.ipynb)
   - **RAG**: Group Chat with Retrieval Augmented Generation (with 5 group member agents and 1 manager agent) - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_groupchat_RAG.ipynb)
   - In-depth Guide to OpenAI Utility Functions - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/oai_openai_utils.ipynb)
   - Function Inception: Enable AutoGen agents to update/remove functions during conversations. - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_inception_function.ipynb)

5. **Agent Teaching and Learning**
   - Teach Agents New Skills & Reuse via Automated Chat - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_teaching.ipynb)
   - Teach Agents New Facts, User Preferences and Skills Beyond Coding - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_teachability.ipynb)

6. **Multi-Agent Chat with OpenAI Assistants in the loop**
   - Hello-World Chat with OpenAi Assistant in AutoGen - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_oai_assistant_twoagents_basic.ipynb)
   - Chat with OpenAI Assistant using Function Call - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_oai_assistant_function_call.ipynb)
   - Chat with OpenAI Assistant with Code Interpreter - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_oai_code_interpreter.ipynb)
   - Chat with OpenAI Assistant with Retrieval Augmentation - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_oai_assistant_retrieval.ipynb)
   - OpenAI Assistant in a Group Chat - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_oai_assistant_groupchat.ipynb)

7. **Multimodal Agent**
   - Multimodal Agent Chat with DALLE and GPT-4V   - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_dalle_and_gpt4v.ipynb)
   - Multimodal Agent Chat with Llava  - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_lmm_llava.ipynb)
   - Multimodal Agent Chat with GPT-4V - [View Notebook](https://github.com/microsoft/autogen/blob/main/notebook/agentchat_lmm_gpt-4v.ipynb)


## Tune Inference Hyperparameters

AutoGen also offers a cost-effective hyperparameter optimization technique [EcoOptiGen](https://arxiv.org/abs/2303.04673) for tuning Large Language Models. The research study finds that tuning hyperparameters can significantly improve the utility of them.
Please find documentation about this feature [here](/docs/Use-Cases/enhanced_inference).

Links to notebook examples:
* [Optimize for Code Generation](https://github.com/microsoft/autogen/blob/main/notebook/oai_completion.ipynb) | [Open in colab](https://colab.research.google.com/github/microsoft/autogen/blob/main/notebook/oai_completion.ipynb)
* [Optimize for Math](https://github.com/microsoft/autogen/blob/main/notebook/oai_chatgpt_gpt4.ipynb) | [Open in colab](https://colab.research.google.com/github/microsoft/autogen/blob/main/notebook/oai_chatgpt_gpt4.ipynb)
