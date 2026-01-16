"""
Simple Weather App using AutoGen
Demonstrates how to create agents that can look up weather information for cities.
"""

import autogen
from autogen import AssistantAgent, UserProxyAgent, config_list_from_json
from autogen.cache import Cache
from typing_extensions import Annotated
from weather_functions import get_weather


def main():
    """
    Main function to run the weather app.
    """
    print("\n🌤️  Welcome to AutoGen Weather App!")
    print("=" * 50)
    print("This app uses AI agents to look up weather information.")
    print("=" * 50 + "\n")

    # Load LLM configuration
    # You can create an OAI_CONFIG_LIST file with your OpenAI API key
    # See: https://microsoft.github.io/autogen/docs/FAQ#set-your-api-endpoints
    try:
        config_list = config_list_from_json(env_or_file="OAI_CONFIG_LIST")
    except Exception as e:
        print(f"Error loading config: {e}")
        print("\nPlease create an OAI_CONFIG_LIST file with your OpenAI API key.")
        print("Example format:")
        print('[')
        print('    {')
        print('        "model": "gpt-4",')
        print('        "api_key": "your-api-key-here"')
        print('    }')
        print(']')
        return

    # Configure LLM settings
    llm_config = {
        "config_list": config_list,
        "timeout": 120,
    }

    # Create the assistant agent (powered by LLM)
    assistant = AssistantAgent(
        name="weather_assistant",
        system_message="You are a helpful weather assistant. Use the get_weather function to provide weather information for cities. Be friendly and concise. Reply TERMINATE when the task is done.",
        llm_config=llm_config,
    )

    # Create the user proxy agent (executes functions)
    user_proxy = UserProxyAgent(
        name="user",
        is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
        human_input_mode="NEVER",
        max_consecutive_auto_reply=10,
        code_execution_config=False,
    )

    # Register the weather function with both agents
    @user_proxy.register_for_execution()
    @assistant.register_for_llm(description="Get current weather information for a specific city.")
    def weather_lookup(
        city: Annotated[str, "Name of the city to get weather for"],
        use_mock: Annotated[bool, "Whether to use mock data (True) or real API (False)"] = True
    ) -> str:
        """
        Look up weather information for a city.

        Args:
            city: Name of the city
            use_mock: If True, uses mock data. If False, uses real OpenWeatherMap API

        Returns:
            JSON string with weather information
        """
        return get_weather(city, use_mock)

    # Example queries to demonstrate the app
    example_queries = [
        "What's the weather in Seoul?",
        "How's the weather in Tokyo and London?",
        "Tell me about the weather conditions in Paris.",
    ]

    print("Running example queries...\n")

    # Run each example query
    for i, query in enumerate(example_queries, 1):
        print(f"\n{'='*60}")
        print(f"Example {i}: {query}")
        print('='*60 + "\n")

        with Cache.disk() as cache:
            user_proxy.initiate_chat(
                assistant,
                message=query,
                cache=cache,
            )

        print("\n")

    print("\n" + "="*60)
    print("✅ All examples completed!")
    print("="*60)
    print("\nTo use this app interactively, you can modify the code to:")
    print("1. Accept user input instead of example queries")
    print("2. Set use_mock=False and configure OPENWEATHER_API_KEY for real data")
    print("3. Integrate with a web interface or CLI\n")


if __name__ == "__main__":
    main()
