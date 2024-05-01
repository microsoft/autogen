# Compressing Text with LLMLingua

Text compression is crucial for optimizing interactions with LLMs, especially when dealing with long prompts that can lead to higher costs and slower response times. LLMLingua is a tool designed to compress prompts effectively, enhancing the efficiency and cost-effectiveness of LLM operations.

This guide introduces LLMLingua's integration with AutoGen, demonstrating how to use this tool to compress text, thereby optimizing the usage of LLMs for various applications.

:::info Requirements
Install `pyautogen[long-context]` and `PyMuPDF`:

```bash
pip install "pyautogen[long-context]" PyMuPDF
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

text_compressor = TextMessageCompressor(text_compressor=LLMLingua())
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
import copy

import autogen
from autogen.agentchat.contrib.capabilities import transform_messages
from typing import Dict, List

config_list = [{"model": "gpt-3.5-turbo", "api_key": os.getenv("OPENAI_API_KEY")}]

# Define your agent; the user proxy and an assistant
assistant = autogen.AssistantAgent(
    "assistant",
    llm_config={"config_list": config_list},
    max_consecutive_auto_reply=1,
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
context_handling.add_to_agent(assistant)

message = "Explain to me what's happening in this research paper.\n" + pdf_text
result = user_proxy.initiate_chat(recipient=assistant, clear_history=True, message=message, silent=True)

print(result.chat_history[1]["content"])
```

```console
The research paper you mentioned, titled "AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation," authored by Qingyun Wu and colleagues, provides a comprehensive discussion on AutoGen, a distinctive framework for building large-language-model (LLM) applications through multi-agent conversations.

Here's a summary of the key points in the research paper:

### 1. **Overview of AutoGen Framework**
   AutoGen is a multi-agent conversational framework designed to facilitate the development of applications utilizing LLMs (Large Language Models) like GPT-4. It provides tools for agent customization, allowing interactions in dynamic and context-aware conversation patterns that can adapt based on user inputs and other environmental considerations.

### 2. **Multi-Agent Conversations**
   The framework supports complex communication patterns between multiple agents, each capable of performing distinct roles within a conversation. This architecture allows AutoGen to decompose complex tasks into smaller, manageable chunks handled by specialized agents, leading to more efficient problem solving.

### 3. **Customizable and Conversable Agents**
   Agents within AutoGen are both customizable and conversable, meaning they can be tailored to meet specific application needs and can engage intelligently in dialogue. This adaptability makes it possible to use the same framework across various domains by altering agent configurations without redesigning the entire system.

### 4. **Hierarchical and Flexible Conversation Structures**
   The paper emphasizes the hierarchical nature of conversations, where some agents may control or guide the flow of interaction, while others execute specific tasks. This setup helps in managing the complexity of conversations and ensuring coherence across the contributions of different agents.

### 5. **Application Areas**
   AutoGen is shown to be applicable in diverse fields ranging from mathematics and coding problem-solving to more sophisticated decision-making and operational research. These applications demonstrate the framework's robustness and flexibility, capable of handling both structured and semi-structured tasks.

### 6. **Open-source and Community Contribution**
   The AutoGen framework is open-source, inviting contributions from developers worldwide. This approach helps in refining the framework, extending its capabilities, and adapting it to new challenges and scenarios.

### 7. **Empirical Studies and Evaluations**
   The paper mentions empirical studies that assess the effectiveness of the AutoGen framework across various applications. These studies typically compare AutoGen's performance against standard baselines or existing solutions to highlight its advantages in terms of flexibility, efficiency, and adaptability.

This paper not only advances the field by introducing a scalable and versatile framework but also opens up several avenues for further research and development in the area of multi-agent systems and LLM applications. If you need to execute any specific actions or require more detailed explanations on any part of the paper, let me know!
```
