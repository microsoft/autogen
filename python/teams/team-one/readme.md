# Environment Configuration for Chat Completion Client

This guide outlines how to configure your environment to use the `create_completion_client_from_env` function, which reads environment variables to return an appropriate `ChatCompletionClient`.

## Azure with Active Directory

To configure for Azure with Active Directory, set the following environment variables:

- `CHAT_COMPLETION_PROVIDER='azure'`
- `CHAT_COMPLETION_KWARGS_JSON` with the following JSON structure:

```json
{
  "api_version": "2024-02-15-preview",
  "azure_endpoint": "REPLACE_WITH_YOUR_ENDPOINT",
  "model_capabilities": {
    "function_calling": true,
    "json_output": true,
    "vision": true
  },
  "azure_ad_token_provider": "DEFAULT",
  "model": "gpt-4o-2024-05-13"
}
```

## With OpenAI

To configure for OpenAI, set the following environment variables:

- `CHAT_COMPLETION_PROVIDER='openai'`
- `CHAT_COMPLETION_KWARGS_JSON` with the following JSON structure:

```json
{
  "api_key": "REPLACE_WITH_YOUR_API",
  "model": "gpt-4o-2024-05-13"
}
```
