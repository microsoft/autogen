# Async Human-in-the-Loop Example

An example showing human-in-the-loop which waits for human input before making the tool call.

## Running the examples

### Prerequisites

First, you need a shell with AutoGen core and required dependencies installed.

```bash
pip install "autogen-core==0.4.0.dev13" "autogen-ext[openai,azure]==0.4.0.dev13"
```

### Using Azure OpenAI API

For Azure OpenAI API, you need to set the following environment variables:

```bash
export OPENAI_API_TYPE=azure
export AZURE_OPENAI_API_ENDPOINT=your_azure_openai_endpoint
export AZURE_OPENAI_API_VERSION=your_azure_openai_api_version
```

By default, we use Azure Active Directory (AAD) for authentication.
You need to run `az login` first to authenticate with Azure.
You can also
use API key authentication by setting the following environment variables:

```bash
export AZURE_OPENAI_API_KEY=your_azure_openai_api_key
```

This requires azure-identity installation:

```bash
pip install azure-identity
```

### Using OpenAI API

For OpenAI API, you need to set the following environment variables.

```bash
export OPENAI_API_TYPE=openai
export OPENAI_API_KEY=your_openai_api_key
```
