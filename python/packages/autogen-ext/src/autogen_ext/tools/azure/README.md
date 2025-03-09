# Azure Tools for AutoGen

This module provides tools for integrating Azure services with AutoGen.

## Azure AI Search Tool

The Azure AI Search tool enables agents to search through documents and data stored in Azure AI Search indexes.

### Installation

```bash
pip install "autogen-ext[azure]"
```

### Features

- **Simple Search**: Basic keyword-based search
- **Semantic Search**: AI-powered search with semantic ranking
- **Vector Search**: Similarity search using embeddings
- **Hybrid Search**: Combines text and vector search for optimal results
- **Resilient Operation**: Built-in retry logic and error handling
- **Environment Variable Support**: Secure credential management

### Usage Examples

#### Basic Setup

```python
from autogen_ext.tools.azure import OpenAIAzureAISearchTool
from azure.core.credentials import AzureKeyCredential
import openai

# Initialize the async OpenAI client
openai_client = openai.AsyncOpenAI(api_key="your-openai-key")

# Create the search tool
search_tool = OpenAIAzureAISearchTool(
    openai_client=openai_client,
    embedding_model="text-embedding-ada-002",
    name="document_search",
    endpoint="https://your-search-service.search.windows.net",
    index_name="your-index",
    credential=AzureKeyCredential("your-api-key"),
    query_type="vector",
    vector_fields=["embedding"]
)

# Use in an async function
async def search_documents():
    from autogen_core import CancellationToken
    
    results = await search_tool.run_json(
        {
            "query": "financial reports",
            "filter": "year eq 2023 and department eq 'Finance'"
        },
        CancellationToken()
    )
    return results
```

#### Using Factory Methods

```python
# Create a semantic search tool
semantic_search = OpenAIAzureAISearchTool.create_semantic_search(
    openai_client=openai_client,
    embedding_model="text-embedding-ada-002",
    name="semantic_search",
    endpoint="https://your-search-service.search.windows.net",
    index_name="your-index",
    credential=AzureKeyCredential("your-api-key"),
    semantic_config_name="default"
)

# Create a vector search tool
vector_search = OpenAIAzureAISearchTool.create_vector_search(
    openai_client=openai_client,
    embedding_model="text-embedding-ada-002",
    name="vector_search",
    endpoint="https://your-search-service.search.windows.net",
    index_name="your-index",
    credential=AzureKeyCredential("your-api-key"),
    vector_fields=["embedding"]
)

# Create a hybrid search tool
hybrid_search = OpenAIAzureAISearchTool.create_hybrid_search(
    openai_client=openai_client,
    embedding_model="text-embedding-ada-002",
    name="hybrid_search",
    endpoint="https://your-search-service.search.windows.net",
    index_name="your-index",
    credential=AzureKeyCredential("your-api-key"),
    vector_fields=["embedding"],
    semantic_config_name="default"
)
```

#### Using Environment Variables

Set up your environment variables:

```bash
export AZURE_SEARCH_ENDPOINT="https://your-search-service.search.windows.net"
export AZURE_SEARCH_INDEX_NAME="your-index"
export AZURE_SEARCH_API_KEY="your-api-key"
export AZURE_SEARCH_QUERY_TYPE="semantic"
export AZURE_SEARCH_SEMANTIC_CONFIG="default"
export AZURE_SEARCH_VECTOR_FIELDS="embedding"
```

Then create the search tool:

```python
# Load configuration from environment variables
search_tool = OpenAIAzureAISearchTool.from_env(
    openai_client=openai_client,
    embedding_model="text-embedding-ada-002",
    name="env_search"
)
```

### Error Handling

The tool includes built-in retry logic for common transient errors:

- Rate limiting
- Network connectivity issues
- Server errors

It uses exponential backoff with jitter to efficiently recover from transient failures.

### Security Best Practices

1. **Use environment variables** instead of hardcoding credentials
2. **Use Azure Key Vault** for storing sensitive credentials
3. **Use managed identities** when running in Azure
4. **Apply least privilege** to your search service API keys
5. **Regularly rotate** your API keys

### Performance Optimization

For bulk operations, use the batched embedding functionality:

```python
async def process_multiple_queries(queries):
    # Process multiple queries in batch for efficiency
    embeddings = await search_tool._get_embeddings_batch(queries)
    # Use embeddings for search or other operations
```

### Debugging

Enable more verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("autogen_ext.tools.azure").setLevel(logging.DEBUG)
```

### Troubleshooting

If you encounter issues:

1. Verify your Azure AI Search service is running
2. Check that your index exists and is properly configured
3. Ensure your API key has appropriate permissions
4. For vector search, confirm your index has vector fields configured 