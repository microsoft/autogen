# Profiler Package

This package introduces a new functionality to profile chat messages. It includes a `Profiler` class that identifies the state of a chat message based on predefined states. The package is primarily focused on creating a profiling tool for chat messages.

## New Classes

- `State` and `StateSpace` classes: Represent a state and a collection of states, respectively. A default state space is also defined. (Located in `profiler/state.py`)

- `Message` and `OpenAIMessage` classes: Represent a chat message and a chat message formatted for the OpenAI API, respectively. (Located in `profiler/message.py`)

- `Profiler`, `MessageProfile`, and `ChatProfile` classes: The `Profiler` class can profile a message and return a `MessageProfile`, which contains the message and the states that apply to the message. A `ChatProfile` is a collection of `MessageProfile` objects. (Located in `profiler/profiler.py`)

- `ChatCompletionService` protocol and `OpenAIJSONService` class: The `OpenAIJSONService` class interacts with the OpenAI API to generate completions. (Located in `profiler/llm.py`)

## Demo

A demonstration of how to use the `Profiler` class to profile a list of chat messages is provided in `demo.py`.

## Usage

To use the `Profiler` class, you need to create an instance of it and call the `profile` method with a list of chat messages as the argument. The `profile` method will return a `ChatProfile` object, which is a collection of `MessageProfile` objects. Each `MessageProfile` object contains a message and the states that apply to the message.

## Installation

To install the package, clone the repository and install the dependencies.

```bash
git clone git@github.com:microsoft/autogen.git
git checkout ct_webarena
cd samples/profiler
pip install -r requirements.txt
python demo.py
```
