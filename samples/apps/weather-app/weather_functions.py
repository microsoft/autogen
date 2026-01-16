"""
Weather API functions for AutoGen weather app.
Supports both real OpenWeatherMap API and mock data for testing.
"""

import os
from typing import Optional, Dict, Any
import json

def get_weather(city: str, use_mock: bool = True) -> str:
    """
    Get current weather information for a specific city.

    Args:
        city: Name of the city to get weather for
        use_mock: If True, use mock data. If False, use real OpenWeatherMap API

    Returns:
        JSON string with weather information including temperature,
        conditions, humidity, and wind speed.
    """
    if use_mock:
        return _get_mock_weather(city)
    else:
        return _get_real_weather(city)


def _get_mock_weather(city: str) -> str:
    """
    Returns mock weather data for testing without API key.
    """
    # Mock weather data for common cities
    mock_data = {
        "seoul": {
            "city": "Seoul",
            "temperature": 5,
            "temperature_unit": "°C",
            "conditions": "Partly Cloudy",
            "humidity": 65,
            "wind_speed": 12,
            "wind_unit": "km/h"
        },
        "new york": {
            "city": "New York",
            "temperature": 32,
            "temperature_unit": "°F",
            "conditions": "Sunny",
            "humidity": 55,
            "wind_speed": 8,
            "wind_unit": "mph"
        },
        "london": {
            "city": "London",
            "temperature": 10,
            "temperature_unit": "°C",
            "conditions": "Rainy",
            "humidity": 85,
            "wind_speed": 15,
            "wind_unit": "km/h"
        },
        "tokyo": {
            "city": "Tokyo",
            "temperature": 8,
            "temperature_unit": "°C",
            "conditions": "Clear",
            "humidity": 60,
            "wind_speed": 10,
            "wind_unit": "km/h"
        },
        "paris": {
            "city": "Paris",
            "temperature": 12,
            "temperature_unit": "°C",
            "conditions": "Cloudy",
            "humidity": 70,
            "wind_speed": 13,
            "wind_unit": "km/h"
        }
    }

    city_lower = city.lower()
    if city_lower in mock_data:
        weather = mock_data[city_lower]
        return json.dumps({
            "success": True,
            "city": weather["city"],
            "temperature": f"{weather['temperature']}{weather['temperature_unit']}",
            "conditions": weather["conditions"],
            "humidity": f"{weather['humidity']}%",
            "wind_speed": f"{weather['wind_speed']} {weather['wind_unit']}",
            "source": "mock_data"
        })
    else:
        return json.dumps({
            "success": True,
            "city": city.title(),
            "temperature": "20°C",
            "conditions": "Partly Cloudy",
            "humidity": "60%",
            "wind_speed": "10 km/h",
            "source": "mock_data",
            "note": "Using default mock data for unknown city"
        })


def _get_real_weather(city: str) -> str:
    """
    Fetches real weather data from OpenWeatherMap API.
    Requires OPENWEATHER_API_KEY environment variable.
    """
    api_key = os.getenv("OPENWEATHER_API_KEY")

    if not api_key:
        return json.dumps({
            "success": False,
            "error": "OPENWEATHER_API_KEY environment variable not set. Set it or use mock mode.",
            "city": city
        })

    try:
        import requests

        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            return json.dumps({
                "success": True,
                "city": data["name"],
                "temperature": f"{data['main']['temp']}°C",
                "conditions": data["weather"][0]["description"].title(),
                "humidity": f"{data['main']['humidity']}%",
                "wind_speed": f"{data['wind']['speed']} m/s",
                "source": "openweathermap_api"
            })
        elif response.status_code == 404:
            return json.dumps({
                "success": False,
                "error": f"City '{city}' not found",
                "city": city
            })
        else:
            return json.dumps({
                "success": False,
                "error": f"API error: {response.status_code}",
                "city": city
            })

    except ImportError:
        return json.dumps({
            "success": False,
            "error": "requests library not installed. Run: pip install requests",
            "city": city
        })
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": f"Error fetching weather: {str(e)}",
            "city": city
        })
