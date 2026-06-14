"""
Dentist Booking Assistant Agent

AI-powered assistant for finding dentists and booking appointments.
Provides detailed dentist profiles with specialties, experience, and availability.

Usage: python agent.py
"""
from pathlib import Path
import asyncio
import json
from agent_framework import Agent, tool, AgentSession
from agent_framework.foundry import FoundryChatClient
from azure.identity import AzureCliCredential
from llm_config import LLMProviderConfig
from functools import cache 
from agent_framework.declarative import AgentFactory
from jinja2 import Environment, FileSystemLoader
from agent_framework.devui import serve 
from azure.monitor.opentelemetry import configure_azure_monitor
from agent_framework.observability import create_resource, enable_instrumentation

llmconfig = LLMProviderConfig()

configure_azure_monitor(
    connection_string=llmconfig.application_insights_connection_string,
    resource=create_resource(),
    enable_live_metrics=True,
)

enable_instrumentation(enable_sensitive_data=True)


@tool()
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



async def main():
      
    # Set up Jinja2 environment
    env = Environment(loader=FileSystemLoader('./prompts'))
    template = env.get_template("instructions.yaml")
    
    yaml_definition = template.render(
    foundry_model=llmconfig.foundry_model, 
    foundry_project_endpoint=llmconfig.foundry_project_endpoint, 
    default_max_tokens=llmconfig.default_max_tokens)

    factory = AgentFactory(
        client_kwargs={"credential": AzureCliCredential()},
        bindings={"get_all_dentists": get_all_dentists},
    )
    agent = factory.create_agent_from_yaml(yaml_definition)
    agent.id = "booking-assistant"

   
    pid = input("Patient Id: ")
    if pid:
        if(file := Path(f"{pid}_session_state.json")).exists():
            # Read the file back
            with open(f"{pid}_session_state.json", "r") as f:
                loaded_dict = json.load(f)
            # Reconstitute the session using the class builder
            session = AgentSession.from_dict(loaded_dict)
        else:
            session = agent.create_session()
    else:
        session = agent.create_session

    session.state["patient_id"] = pid
    
    while True:
        user_input = input("User: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Exiting...")
            break
        
        reasoning_parts = []
        text_parts = []

        async for response_stream in agent.run(
            user_input,
            stream=True,
            session=session,
            options={"reasoning": {"effort" : "medium", "summary": "concise" }}
        ):
            for content in response_stream.contents:
                if content.type == "text_reasoning":
                    reasoning_parts.append(content.text)
                elif content.type == "text":
                    text_parts.append(content.text)


        # Print reasoning once
        if reasoning_parts:
            reasoning_text = "".join(reasoning_parts).strip()
            print("\n\nReasoning:")
            print(reasoning_text)

        print("\n\nFinal Answer:")
        print("".join(text_parts).strip())
        print("\n" + "="*50 + "\n")
    
    print("Conversation ended.")
    print(session.service_session_id)

    # Extract session state to a dictionary
    session_dict = session.to_dict() 

    # Save the dictionary as a JSON file
    with open(f"{pid}_session_state.json", "w") as f:
        json.dump(session_dict, f)


if __name__ == "__main__":
    #serve(entities=[agent], auto_open=True)
    asyncio.run(main())
    
