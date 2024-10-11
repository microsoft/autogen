# What Next?

Now that you have learned the basics of AutoGen, you can start to build your own
agents. Here are some ideas to get you started without going to the advanced
topics:

1.  **Chat with LLMs**: In [Human in the Loop](./human-in-the-loop) we covered
    the basic human-in-the-loop usage. You can try to hook up different LLMs
    using local model servers like
    [Ollama](https://github.com/ollama/ollama)
    and [LM Studio](https://lmstudio.ai/), and
    chat with them using the human-in-the-loop component of your human proxy
    agent.
2.  **Prompt Engineering**: In [Code Executors](./code-executors) we
    covered the simple two agent scenario using GPT-4 and Python code executor.
    To make this scenario work for different LLMs and programming languages, you
    probably need to tune the system message of the code writer agent. Same with
    other scenarios that we have covered in this tutorial, you can also try to
    tune system messages for different LLMs.
3.  **Complex Tasks**: In [ConversationPatterns](./conversation-patterns)
    we covered the basic conversation patterns. You can try to find other tasks
    that can be decomposed into these patterns, and leverage the code executors
    and tools
    to make the agents more powerful.

## Dig Deeper

- Read the [user guide](/docs/topics) to learn more
- Read the examples and guides in the [notebooks section](/docs/notebooks)
- Check [research](/docs/Research) and [blog](/blog)

## Get Help

If you have any questions, you can ask in our [GitHub
Discussions](https://github.com/microsoft/autogen/discussions).

[![](https://img.shields.io/discord/1153072414184452236?logo=discord&style=flat.png)](https://aka.ms/autogen-dc)

## Get Involved

- Check out [Roadmap Issues](https://aka.ms/autogen-roadmap) to see what we are working on.
- Contribute your work to our [gallery](/docs/Gallery)
- Follow our [contribution guide](/docs/contributor-guide/contributing) to make a pull request to AutoGen
- You can also share your work with the community on the Discord server.
