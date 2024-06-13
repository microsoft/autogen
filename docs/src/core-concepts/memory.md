# Memory

Memory is a collection of data corresponding to the conversation history
of an agent.
Data in meory can be just a simple list of all messages,
or one which provides a view of the last N messages
({py:class}`agnext.chat.memory.BufferedChatMemory`).

Built-in memory implementations are:

- {py:class}`agnext.chat.memory.BufferedChatMemory`
- {py:class}`agnext.chat.memory.HeadAndTailChatMemory`

To create a custom memory implementation, you need to subclass the
{py:class}`agnext.chat.memory.ChatMemory` protocol class and implement
all its methods.
For example, you can use [LLMLingua](https://github.com/microsoft/LLMLingua)
to create a custom memory implementation that provides a compressed
view of the conversation history.
