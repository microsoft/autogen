# AutoGen Agent Profiler

This repository contains utilities that provide visibility into the activities of AI agents. Currently, there are two main utilities: `annotate_chat_history` and `draw_profiler_graph`.

## Utilities

### annotate_chat_history

This utility takes a chat history as input and annotates it using GPT-4. It predicts if a predefined set of codes apply to a given message. The output is an annotated chat history.

### draw_profiler_graph

This utility takes the annotated chat history from `annotate_chat_history` as input and generates a graph. This graph provides a visual representation of the agent's activities over time.

## Interpreting the Chart

To interpret the resulting chart, look for patterns in the agent's activities. For example, if a certain code is frequently applied, it might indicate that the agent often performs a certain action.



## Example Usage

- [Two Agents](../../../../notebook/agentchat_profiler.ipynb)
- [Group Chat](../../../../notebook/agentchat_profiler_groupchat.ipynb)
