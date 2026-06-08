# AgentChat Message ID System

## Overview
As part of GitHub issue #6317, all AgentChat messages and events now include a unique `id` field. This enhancement allows for better tracking of messages and correlation between streaming chunks and the final completed message.

## Key Changes
- **`BaseChatMessage`**: Added `id: str` field with a default UUID4 factory.
- **`BaseAgentEvent`**: Added `id: str` field with a default UUID4 factory.
- **`ModelClientStreamingChunkEvent`**: Includes `full_message_id: str | None` to correlate chunks with the final message.
- **Agents**: Updated `AssistantAgent`, `CodeExecutorAgent`, and `SelectorGroupChatManager` to generate and maintain consistent IDs during streaming.

## Backward Compatibility
The system is fully backward compatible:
1.  **Missing IDs**: When loading messages from JSON that lack an `id` field, a new UUID is automatically generated.
2.  **Serialization**: The `id` field is included in the JSON output by default via Pydantic's `model_dump`.

## Usage Examples

### Accessing Message ID
```python
msg = TextMessage(content="Hello", source="user")
print(msg.id)  # Outputs a UUID string
```

### Correlation in Streaming
```python
# Streaming chunks will have the same full_message_id as the final message's id
async for message in agent.on_messages_stream(messages):
    if isinstance(message, ModelClientStreamingChunkEvent):
        print(f"Chunk for message {message.full_message_id}: {message.content}")
    elif isinstance(message, Response):
        print(f"Final message {message.chat_message.id}: {message.chat_message.content}")
```

## Migration Notes
- If you were previously relying on custom message dictionaries without an `id` field, you may notice an `id` field appearing when serializing messages.
- No code changes are required for existing applications unless you wish to utilize the new ID field for tracking or correlation.
- If you have custom message types inheriting from `BaseChatMessage` or `BaseAgentEvent`, they will automatically inherit the `id` field.
