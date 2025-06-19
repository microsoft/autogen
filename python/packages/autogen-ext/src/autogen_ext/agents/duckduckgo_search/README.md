# DuckDuckGo Search Agent

A specialized AutoGen agent that uses DuckDuckGo for web searches, providing privacy-focused search capabilities without requiring API keys.

## Overview

The DuckDuckGo Search Agent is built on top of AutoGen's `AssistantAgent` and comes pre-configured with a DuckDuckGo search tool. It's designed for research and information gathering tasks while respecting user privacy.

### Key Features

- **No API Key Required**: Uses DuckDuckGo's HTML interface directly
- **Privacy-Focused**: DuckDuckGo doesn't track users or store search history
- **Content Extraction**: Can fetch and parse webpage content in markdown format
- **Configurable Results**: Control number of results, snippets, and content inclusion
- **Built-in Safety**: Includes safe search and region filtering options

## Installation

### Simple Installation (Recommended)

Install AutoGen Extensions with DuckDuckGo search dependencies:

```bash
pip install autogen-ext[duckduckgo-search]
```

This automatically installs all required dependencies:
- `httpx>=0.27.0` - For HTTP requests
- `beautifulsoup4>=4.12.0` - For HTML parsing  
- `html2text>=2024.2.26` - For converting HTML to text
- `autogen-agentchat==0.6.1` - For agent functionality

### Manual Installation

Alternatively, you can install dependencies manually:

```bash
pip install httpx beautifulsoup4 html2text
pip install autogen-ext
```

## Quick Start

### Basic Usage

```python
import asyncio
from autogen_ext.agents.duckduckgo_search import DuckDuckGoSearchAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

async def main():
    # Create a model client
    model_client = OpenAIChatCompletionClient(
        model="gpt-4o-mini",
        api_key="your-openai-api-key"
    )
    
    # Create the DuckDuckGo search agent
    agent = DuckDuckGoSearchAgent(
        name="research_agent",
        model_client=model_client
    )
    
    # Use the agent to perform research
    result = await agent.run(
        task="Find information about the latest developments in renewable energy"
    )
    
    print(result.messages[-1].content)

asyncio.run(main())
```

### Using the Search Tool Directly

```python
import asyncio
from autogen_ext.tools.web_search import DuckDuckGoSearchTool
from autogen_ext.tools.web_search._duckduckgo_search import DuckDuckGoSearchArgs
from autogen_core import CancellationToken

async def search_example():
    # Create the search tool
    search_tool = DuckDuckGoSearchTool()
    
    # Configure search parameters
    search_args = DuckDuckGoSearchArgs(
        query="Python machine learning libraries",
        num_results=5,
        include_snippets=True,
        include_content=True,
        content_max_length=5000
    )
    
    # Perform the search
    result = await search_tool.run(search_args, CancellationToken())
    
    # Process results
    for search_result in result.results:
        print(f"Title: {search_result['title']}")
        print(f"URL: {search_result['url']}")
        if search_result.get('snippet'):
            print(f"Snippet: {search_result['snippet']}")
        print("---")

asyncio.run(search_example())
```

## Configuration Options

### DuckDuckGoSearchAgent Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | Required | Name of the agent |
| `model_client` | `ChatCompletionClient` | Required | Model client for AI responses |
| `description` | `str` | Auto-generated | Description of the agent's capabilities |
| `system_message` | `str` | Auto-generated | System prompt for the agent |
| `num_results` | `int` | `3` | Default number of search results |
| `include_content` | `bool` | `True` | Whether to fetch webpage content |
| `content_max_length` | `int` | `10000` | Maximum content length per page |

### DuckDuckGoSearchArgs Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str` | Required | Search query string |
| `num_results` | `int` | `3` | Number of results to return (max 10) |
| `include_snippets` | `bool` | `True` | Include result snippets |
| `include_content` | `bool` | `True` | Fetch full webpage content |
| `content_max_length` | `int` | `10000` | Max content length per page |
| `language` | `str` | `"en"` | Search language |
| `region` | `str` | `None` | Search region (e.g., "us-en") |
| `safe_search` | `bool` | `True` | Enable safe search filtering |

## Advanced Usage

### Custom Agent Configuration

```python
from autogen_ext.agents.duckduckgo_search import DuckDuckGoSearchAgent

# Create agent with custom settings
agent = DuckDuckGoSearchAgent(
    name="specialized_researcher",
    model_client=model_client,
    description="A specialized research agent for academic papers",
    system_message="""You are an academic research assistant. 
    When searching, focus on scholarly sources and peer-reviewed content.
    Always cite your sources and provide detailed analysis.""",
    num_results=5,
    include_content=True,
    content_max_length=15000
)
```

### Multi-Language Search

```python
from autogen_ext.tools.web_search._duckduckgo_search import DuckDuckGoSearchArgs

# Search in Spanish
search_args = DuckDuckGoSearchArgs(
    query="inteligencia artificial",
    language="es",
    region="es-es",
    num_results=3
)
```

### Content-Only Search (Faster)

```python
# For faster searches without content extraction
search_args = DuckDuckGoSearchArgs(
    query="latest tech news",
    include_content=False,
    include_snippets=True,
    num_results=10
)
```

## Integration Examples

### Team-Based Research

```python
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.agents.duckduckgo_search import DuckDuckGoSearchAgent

# Create a research team
researcher = DuckDuckGoSearchAgent(
    name="researcher",
    model_client=model_client,
    description="Finds and gathers information"
)

analyst = AssistantAgent(
    name="analyst",
    model_client=model_client,
    description="Analyzes and synthesizes research findings",
    system_message="Analyze the research findings and provide insights."
)

# Create team
team = RoundRobinGroupChat(
    participants=[researcher, analyst],
    termination_condition=TextMentionTermination("TERMINATE")
)

# Run research task
result = await team.run(
    task="Research the impact of AI on healthcare and provide analysis"
)
```

### Streaming Results

```python
# Use streaming for real-time results
async for message in agent.run_stream(
    task="Find the latest news about space exploration"
):
    print(f"{message.source}: {message.content}")
```

## Error Handling

The DuckDuckGo search tool includes robust error handling:

```python
try:
    result = await search_tool.run(search_args, cancellation_token)
    if not result.results:
        print("No results found")
    else:
        print(f"Found {len(result.results)} results")
except Exception as e:
    print(f"Search failed: {e}")
```

Common error scenarios:
- Network connectivity issues
- Invalid search parameters
- Rate limiting (rare with DuckDuckGo)
- Content parsing errors

## Performance Considerations

### Optimization Tips

1. **Disable Content Fetching**: Set `include_content=False` for faster searches
2. **Limit Results**: Use fewer `num_results` for quicker responses
3. **Content Length**: Reduce `content_max_length` to minimize processing time
4. **Caching**: Implement caching for repeated queries

### Resource Usage

- **Memory**: Content fetching can use significant memory for large pages
- **Network**: Each result with content requires additional HTTP requests
- **Time**: Content extraction adds 1-3 seconds per page

## Testing

### Unit Tests

Run the unit tests to verify functionality:

```bash
cd python/packages/autogen-ext
python -m pytest tests/tools/web_search/test_duckduckgo_search.py -v
python -m pytest tests/tools/web_search/test_duckduckgo_agent.py -v
```

### Integration Tests

Run integration tests (requires network access):

```bash
python -m pytest tests/tools/web_search/test_integration.py -v -m integration
```


## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   pip install httpx beautifulsoup4 html2text
   ```

2. **No Results Found**
   - Check internet connectivity
   - Try different search terms
   - Verify query parameters

3. **Content Parsing Errors**
   - Some websites may block automated access
   - Try setting `include_content=False`
   - Check for JavaScript-heavy sites

4. **Slow Performance**
   - Reduce `num_results`
   - Disable content fetching
   - Implement result caching

### Debug Mode

Enable debug logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

Follow Autogen repo guidelines.

## License

This implementation is part of the AutoGen project and follows the same license terms.

## Support

For issues and questions:
- Check the [AutoGen documentation](https://microsoft.github.io/autogen/)
- Open an issue on the [AutoGen GitHub repository](https://github.com/microsoft/autogen)
- Review the test files for usage examples