import os
import asyncio
from dotenv import load_dotenv
from agent_framework import Agent
from agent_framework.openai import OpenAIChatClient


# Load environment variables
load_dotenv()


# Define the get_weather tool
def get_weather(location: str) -> str:
    """
    Get the current weather for a given location.
    
    Args:
        location: The city or location name
        
    Returns:
        Weather information for the location
    """

    print(f"Fetching weather data for {location}...")  # Debug statement
    # Mock weather data for demonstration
    weather_data = {
        "Dubai": "Sunny, 35°C, 10% chance of rain",
        "London": "Cloudy, 25°C, 60% chance of rain",
        "Karachi": "Sunny, 40°C, 5% chance of rain"
    }
    
    return weather_data.get(location, f"Weather data for {location} is not available.")


async def main():
    # Initialize a chat agent with OpenAI
    agent = Agent(
        client=OpenAIChatClient(
            api_key=os.environ.get("OPENAI_API_KEY"),
            model=os.environ.get("OPENAI_MODEL", "gpt-4"),
        ),
        name="WeatherAssistant",
        instructions="You are a helpful weather assistant. When users ask about the weather, use the get_weather tool to fetch the current conditions for their location.",
        tools=[get_weather],  # Register the get_weather tool
    )

    # Example: Ask the agent about the weather
    response = await agent.run("What's the weather like in Karachi, London and Dubai?")
    print(f"Agent: {response}")


if __name__ == "__main__":
    asyncio.run(main())
