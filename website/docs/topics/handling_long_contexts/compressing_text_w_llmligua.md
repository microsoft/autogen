# Compressing Text with LLMLingua

Text compression is crucial for optimizing interactions with LLMs, especially when dealing with long prompts that can lead to higher costs and slower response times. LLMLingua is a tool designed to compress prompts effectively, enhancing the efficiency and cost-effectiveness of LLM operations.

This guide introduces LLMLingua's integration with AutoGen, demonstrating how to use this tool to compress text, thereby optimizing the usage of LLMs for various applications.

:::info Requirements
Install `autogen-agentchat[long-context]~=0.2` and `PyMuPDF`:

```bash
pip install "autogen-agentchat[long-context]~=0.2" PyMuPDF
```

For more information, please refer to the [installation guide](/docs/installation/).
:::

## Example 1: Compressing AutoGen Research Paper using LLMLingua

We will look at how we can use `TextMessageCompressor` to compress an AutoGen research paper using `LLMLingua`. Here's how you can initialize `TextMessageCompressor` with LLMLingua, a text compressor that adheres to the `TextCompressor` protocol.

```python
import tempfile

import fitz  # PyMuPDF
import requests

from autogen.agentchat.contrib.capabilities.text_compressors import LLMLingua
from autogen.agentchat.contrib.capabilities.transforms import TextMessageCompressor

AUTOGEN_PAPER = "https://arxiv.org/pdf/2308.08155"


def extract_text_from_pdf():
    # Download the PDF
    response = requests.get(AUTOGEN_PAPER)
    response.raise_for_status()  # Ensure the download was successful

    text = ""
    # Save the PDF to a temporary file
    with tempfile.TemporaryDirectory() as temp_dir:
        with open(temp_dir + "temp.pdf", "wb") as f:
            f.write(response.content)

        # Open the PDF
        with fitz.open(temp_dir + "temp.pdf") as doc:
            # Read and extract text from each page
            for page in doc:
                text += page.get_text()

    return text


# Example usage
pdf_text = extract_text_from_pdf()

llm_lingua = LLMLingua()
text_compressor = TextMessageCompressor(text_compressor=llm_lingua)
compressed_text = text_compressor.apply_transform([{"content": pdf_text}])

print(text_compressor.get_logs([], []))
```

```console
('19765 tokens saved with text compression.', True)
```

## Example 2: Integrating LLMLingua with `ConversableAgent`

Now, let's integrate `LLMLingua` into a conversational agent within AutoGen. This allows dynamic compression of prompts before they are sent to the LLM.

```python
import os

import autogen
from autogen.agentchat.contrib.capabilities import transform_messages

system_message = "You are a world class researcher."
config_list = [{"model": "gpt-4-turbo", "api_key": os.getenv("OPENAI_API_KEY")}]

# Define your agent; the user proxy and an assistant
researcher = autogen.ConversableAgent(
    "assistant",
    llm_config={"config_list": config_list},
    max_consecutive_auto_reply=1,
    system_message=system_message,
    human_input_mode="NEVER",
)
user_proxy = autogen.UserProxyAgent(
    "user_proxy",
    human_input_mode="NEVER",
    is_termination_msg=lambda x: "TERMINATE" in x.get("content", ""),
    max_consecutive_auto_reply=1,
)
```

:::tip
Learn more about configuring LLMs for agents [here](/docs/topics/llm_configuration).
:::

```python
context_handling = transform_messages.TransformMessages(transforms=[text_compressor])
context_handling.add_to_agent(researcher)

message = "Summarize this research paper for me, include the important information" + pdf_text
result = user_proxy.initiate_chat(recipient=researcher, clear_history=True, message=message, silent=True)

print(result.chat_history[1]["content"])
```

```console
19953 tokens saved with text compression.
The paper describes AutoGen, a framework designed to facilitate the development of diverse large language model (LLM) applications through conversational multi-agent systems. The framework emphasizes customization and flexibility, enabling developers to define agent interaction behaviors in natural language or computer code.

Key components of AutoGen include:
1. **Conversable Agents**: These are customizable agents designed to operate autonomously or through human interaction. They are capable of initiating, maintaining, and responding within conversations, contributing effectively to multi-agent dialogues.

2. **Conversation Programming**: AutoGen introduces a programming paradigm centered around conversational interactions among agents. This approach simplifies the development of complex applications by streamlining how agents communicate and interact, focusing on conversational logic rather than traditional coding for
mats.

3. **Agent Customization and Flexibility**: Developers have the freedom to define the capabilities and behaviors of agents within the system, allowing for a wide range of applications across different domains.

4. **Application Versatility**: The paper outlines various use cases from mathematics and coding to decision-making and entertainment, demonstrating AutoGen's ability to cope with a broad spectrum of complexities and requirements.

5. **Hierarchical and Joint Chat Capabilities**: The system supports complex conversation patterns including hierarchical and multi-agent interactions, facilitating robust dialogues that can dynamically adjust based on the conversation context and the agents' roles.

6. **Open-source and Community Engagement**: AutoGen is presented as an open-source framework, inviting contributions and adaptations from the global development community to expand its capabilities and applications.

The framework's architecture is designed so that it can be seamlessly integrated into existing systems, providing a robust foundation for developing sophisticated multi-agent applications that leverage the capabilities of modern LLMs. The paper also discusses potential ethical considerations and future improvements, highlighting the importance of continual development in response to evolving tech landscapes and user needs.
```

## Example 3: Modifying LLMLingua's Compression Parameters

LLMLingua's flexibility allows for various configurations, such as customizing instructions for the LLM or setting specific token counts for compression. This example demonstrates how to set a target token count, enabling the use of models with smaller context sizes like gpt-3.5.

```python
config_list = [{"model": "gpt-3.5-turbo", "api_key": os.getenv("OPENAI_API_KEY")}]
researcher = autogen.ConversableAgent(
    "assistant",
    llm_config={"config_list": config_list},
    max_consecutive_auto_reply=1,
    system_message=system_message,
    human_input_mode="NEVER",
)

text_compressor = TextMessageCompressor(
    text_compressor=llm_lingua,
    compression_params={"target_token": 13000},
    cache=None,
)
context_handling = transform_messages.TransformMessages(transforms=[text_compressor])
context_handling.add_to_agent(researcher)

compressed_text = text_compressor.apply_transform([{"content": message}])

result = user_proxy.initiate_chat(recipient=researcher, clear_history=True, message=message, silent=True)

print(result.chat_history[1]["content"])
```

```console
25308 tokens saved with text compression.
Based on the extensive research paper information provided, it seems that the focus is on developing a framework called AutoGen for creating multi-agent conversations based on Large Language Models (LLMs) for a variety of applications such as math problem solving, coding, decision-making, and more.

The paper discusses the importance of incorporating diverse roles of LLMs, human inputs, and tools to enhance the capabilities of the conversable agents within the AutoGen framework. It also delves into the effectiveness of different systems in various scenarios, showcases the implementation of AutoGen in pilot studies, and compares its performance with other systems in tasks like math problem-solving, coding, and decision-making.

The paper also highlights the different features and components of AutoGen such as the AssistantAgent, UserProxyAgent, ExecutorAgent, and GroupChatManager, emphasizing its flexibility, ease of use, and modularity in managing multi-agent interactions. It presents case analyses to demonstrate the effectiveness of AutoGen in various applications and scenarios.

Furthermore, the paper includes manual evaluations, scenario testing, code examples, and detailed comparisons with other systems like ChatGPT, OptiGuide, MetaGPT, and more, to showcase the performance and capabilities of the AutoGen framework.

Overall, the research paper showcases the potential of AutoGen in facilitating dynamic multi-agent conversations, enhancing decision-making processes, and improving problem-solving tasks with the integration of LLMs, human inputs, and tools in a collaborative framework.
```
