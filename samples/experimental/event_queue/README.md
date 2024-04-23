## Event Queue Package

This package provides a framework for creating an event-driven system with multiple agents. It's built with Python and uses asyncio for handling asynchronous tasks.

### Components
The package consists of several components:

- `Agent`: A base class for creating agents that can subscribe to events and post events to the event queue.
- `AsyncEventQueue`: A class that manages the event queue. It allows agents to subscribe to specific types of events and post events to the queue.
- `Events`: This module defines several classes for different types of events, such as `NewMessageEvent` and `SafetyAssessment`.
- `LLMAgent`: An agent that uses the OpenAI API to generate responses to messages.
- `MonitoringAgent`: An agent that prints new messages and safety assessments to the console.
- `SafetyAgent`: An agent that assesses the safety of messages.
- `UserAgent`: An agent that gets user input and posts it as a new message event.

### Demo
The `demo.py` script demonstrates how to use the package. It creates a simple chat application with a `UserAgent` and an `LLMAgent`. The `UserAgent` gets input from the user and posts it as a new message event. The `LLMAgent` uses the OpenAI API to generate a response to the message and posts it as a new message event.

The script also creates a `MonitoringAgent` and a `SafetyAgent`. The `MonitoringAgent` prints all new messages and safety assessments to the console. The `SafetyAgent` assesses the safety of messages and posts safety assessments to the event queue.

To run the demo, you need to set the `OPENAI_API_KEY` environment variable to your OpenAI API key. Then, you can run the script with the following command:

```bash
python demo.py
```

This will start the chat application. You can type messages at the prompt, and the LLMAgent will respond to them. The MonitoringAgent will print all messages and safety assessments to the console.
