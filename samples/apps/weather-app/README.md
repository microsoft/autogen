# Weather App with AutoGen

A simple weather application that demonstrates how to use AutoGen's multi-agent framework to look up weather information for cities around the world.

## Features

- 🤖 **AI-Powered**: Uses AutoGen agents with LLM to understand natural language queries
- 🌍 **Global Coverage**: Look up weather for any city worldwide
- 🔄 **Mock Mode**: Test without API keys using built-in mock data
- 🌐 **Real API Support**: Connect to OpenWeatherMap API for live weather data
- 💬 **Natural Conversation**: Ask about weather in conversational language

## How It Works

This app uses AutoGen's agent framework with two agents:
- **Weather Assistant**: An AI agent powered by GPT that understands user queries
- **User Proxy**: An agent that executes the weather lookup function

The agents communicate to:
1. Understand the user's question about weather
2. Call the appropriate weather function
3. Format and return the results in a friendly way

## Prerequisites

- Python 3.8 or higher
- OpenAI API key (for the LLM)
- OpenWeatherMap API key (optional, for real weather data)

## Installation

1. Navigate to the weather-app directory:
```bash
cd samples/apps/weather-app
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your OpenAI API key:

Create a file named `OAI_CONFIG_LIST` in the current directory:
```json
[
    {
        "model": "gpt-4",
        "api_key": "your-openai-api-key-here"
    }
]
```

Or set it as an environment variable:
```bash
export OAI_CONFIG_LIST='[{"model": "gpt-4", "api_key": "your-api-key"}]'
```

4. (Optional) For real weather data, set your OpenWeatherMap API key:
```bash
export OPENWEATHER_API_KEY="your-openweathermap-api-key"
```

Get a free API key at: https://openweathermap.org/api

## Usage

### Run the Example

```bash
python main.py
```

This will run pre-configured example queries:
- "What's the weather in Seoul?"
- "How's the weather in Tokyo and London?"
- "Tell me about the weather conditions in Paris."

### Using Mock Data (Default)

By default, the app uses mock weather data so you can test it without an OpenWeatherMap API key:

```python
get_weather("Seoul", use_mock=True)
```

Mock data is available for:
- Seoul
- New York
- London
- Tokyo
- Paris
- Other cities (returns default values)

### Using Real API

To use real weather data:

1. Set the `OPENWEATHER_API_KEY` environment variable
2. Modify the `use_mock` parameter in `main.py`:

```python
@user_proxy.register_for_execution()
@assistant.register_for_llm(description="Get current weather information for a specific city.")
def weather_lookup(
    city: Annotated[str, "Name of the city to get weather for"],
    use_mock: Annotated[bool, "Whether to use mock data (True) or real API (False)"] = False  # Changed to False
) -> str:
    return get_weather(city, use_mock)
```

### Interactive Mode

To make the app interactive, modify `main.py` to accept user input:

```python
# Replace the example queries section with:
while True:
    user_query = input("\nAsk about weather (or 'exit' to quit): ")
    if user_query.lower() == 'exit':
        break

    with Cache.disk() as cache:
        user_proxy.initiate_chat(
            assistant,
            message=user_query,
            cache=cache,
        )
```

## Example Output

```
🌤️  Welcome to AutoGen Weather App!
==================================================
This app uses AI agents to look up weather information.
==================================================

============================================================
Example 1: What's the weather in Seoul?
============================================================

user (to weather_assistant):

What's the weather in Seoul?

--------------------------------------------------------------------------------

weather_assistant (to user):

***** Suggested tool call: weather_lookup *****
Arguments:
{
  "city": "Seoul",
  "use_mock": true
}
************************************************

--------------------------------------------------------------------------------

***** Response from calling tool *****
{
  "success": true,
  "city": "Seoul",
  "temperature": "5°C",
  "conditions": "Partly Cloudy",
  "humidity": "65%",
  "wind_speed": "12 km/h",
  "source": "mock_data"
}
***************************************

--------------------------------------------------------------------------------

weather_assistant (to user):

The current weather in Seoul is:
- Temperature: 5°C
- Conditions: Partly Cloudy
- Humidity: 65%
- Wind Speed: 12 km/h

TERMINATE
```

## File Structure

```
weather-app/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── main.py                   # Main application entry point
└── weather_functions.py      # Weather API functions (mock & real)
```

## Customization

### Add More Cities to Mock Data

Edit `weather_functions.py` and add entries to the `mock_data` dictionary:

```python
mock_data = {
    "new_city": {
        "city": "New City",
        "temperature": 22,
        "temperature_unit": "°C",
        "conditions": "Sunny",
        "humidity": 50,
        "wind_speed": 10,
        "wind_unit": "km/h"
    },
    # ... other cities
}
```

### Change the LLM Model

Edit the `OAI_CONFIG_LIST` file to use a different model:

```json
[
    {
        "model": "gpt-3.5-turbo",
        "api_key": "your-api-key"
    }
]
```

### Customize Agent Behavior

Modify the `system_message` in `main.py`:

```python
assistant = AssistantAgent(
    name="weather_assistant",
    system_message="Your custom instructions here...",
    llm_config=llm_config,
)
```

## Troubleshooting

### "Error loading config"
- Make sure you have created the `OAI_CONFIG_LIST` file with valid JSON
- Check that your OpenAI API key is correct

### "OPENWEATHER_API_KEY environment variable not set"
- This is normal if using mock mode
- To use real data, set the environment variable: `export OPENWEATHER_API_KEY="your-key"`

### "requests library not installed"
- Install it with: `pip install requests`

## Learn More

- [AutoGen Documentation](https://microsoft.github.io/autogen/)
- [AutoGen GitHub](https://github.com/microsoft/autogen)
- [OpenWeatherMap API](https://openweathermap.org/api)
- [Function Calling Examples](https://microsoft.github.io/autogen/docs/topics/non-openai-models/about-using-nonopenai-models)

## License

This example follows the AutoGen project license.
