"""
Dentist Booking Assistant Agent

AI-powered assistant for finding dentists and booking appointments.
Provides detailed dentist profiles with specialties, experience, and availability.

Usage: python agent.py
"""


import asyncio
from agent_framework import Agent, tool
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential
from llm_config import LLMProviderConfig
from functools import cache 
from agent_framework.devui import serve 

llmconfig = LLMProviderConfig()

PROMPT = """You are a dentist clinic booking assistant. 
            Help users find suitable dentists by using the get_all_dentists tool to access dentist profiles. 
            Provide detailed information about dentists and make recommendations based on user needs."""

@tool
def get_all_dentists() -> list:
    """Return all dentist profiles loaded from the JSON data folder."""
    return [{
                "id": 1,
                "name": "Dr. Jane Smith",
                "specialty": "General Dentistry & Preventive Care",
                "education": [
                    "DDS - University of California, San Francisco",
                    "Bachelor of Science in Biology - Stanford University"
                ],
                "years_of_experience": 12,
                "daily_working_hours": "9:00 AM - 5:00 PM (Monday-Friday), 9:00 AM - 2:00 PM (Saturday)",
                "strengths": [
                    "Patient communication",
                    "Root canal therapy",
                    "Cosmetic dentistry",
                    "Pediatric dentistry"
                ],
                "certifications": [
                    "Board Certified - American Dental Association",
                    "Advanced Life Support (ALS) Certified",
                    "Invisalign Provider Certification"
                ]
                }
            ]

@cache
def get_chat_client():
    """Initialize and return the FoundryChatClient with Azure credentials."""
    return FoundryChatClient(
            project_endpoint=llmconfig.foundry_project_endpoint,
            model=llmconfig.foundry_model,
            credential=AzureCliCredential()
    )

   
agent = Agent(
        client=get_chat_client(),
        name="BookingAssistant",
        instructions=PROMPT,
        tools=[get_all_dentists],
        default_options= {"temperature": llmconfig.default_temperature, "max_tokens": llmconfig.default_max_tokens} 
    )

if __name__ == "__main__":
    serve(entities=[agent], auto_open=True)
