# Ecosystem

This page lists libraries that have integrations with Autogen for LLM applications using multiple agents in alphabetical order. Including your own integration to this list is highly encouraged. Simply open a pull request with a few lines of text, see the dropdown below for more information.


## [MemGPT + AutoGen](https://memgpt.readthedocs.io/en/latest/autogen/)


![Agent Chat Example](img/ecosystem-memgpt.png)

Memory-GPT (or MemGPT in short) is a system that intelligently manages different memory tiers in LLMs in order to effectively provide extended context within the LLM's limited context window. For example, MemGPT knows when to push critical information to a vector database and when to retrieve it later in the chat, enabling perpetual conversations. This integration allows you to equip any AutoGen agent with MemGPT.
