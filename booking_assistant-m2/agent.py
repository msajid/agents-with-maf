"""
Dentist Booking Assistant Agent

AI-powered assistant for finding dentists and booking appointments.

Usage:
python agent.py
"""

import asyncio
import json
from agent_framework import AgentSession
from middlewares.security_middleware import SecurityAgentMiddleware
from context_providers.current_datetime import CurrentDatetimeProvider
from context_providers.patient_id import PatientIdProvider
from agent_framework.declarative import AgentFactory
from azure.identity import AzureCliCredential
from jinja2 import Environment, FileSystemLoader
from azure.monitor.opentelemetry import configure_azure_monitor
from agent_framework.observability import create_resource, enable_instrumentation
from llm_config import LLMProviderConfig
from tools import (
    write_json,
    read_json,
    load_patient_appointments,
    patient_folder,
    load_patient,
    get_all_dentists,
    get_free_slots,
    book_appointment,
    get_appointment_details
)


llmconfig = LLMProviderConfig()


if llmconfig.application_insights_connection_string:
    configure_azure_monitor(
        connection_string=llmconfig.application_insights_connection_string,
        resource=create_resource(),
        enable_live_metrics=True,
    )

    enable_instrumentation(enable_sensitive_data=True)


def load_or_create_patient_session(agent, patient_id: str) -> AgentSession:
    """
    Load an existing AgentSession for the patient from disk,
    or create a new session if no saved session exists.
    """

    patient_profile = load_patient(patient_id)

    if not patient_profile:
        raise ValueError(f"No patient found with id {patient_id}.")

    session_path = patient_folder(patient_id) / "session.json"

    if session_path.exists():
        session_dict = read_json(session_path, {})
        session = AgentSession.from_dict(session_dict)
    else:
        session = agent.create_session()

    appointments = load_patient_appointments(patient_id)

    session.state["patient_id"] = patient_id
    session.state["appointments"] = appointments

    return session

def save_patient_session(patient_id: str, session: AgentSession) -> None:
   
    session_path = patient_folder(patient_id) / "session.json"

    appointments = load_patient_appointments(patient_id)

    session.state["patient_id"] = patient_id
    session.state["appointments"] = appointments

    write_json(session_path, session.to_dict())


def create_booking_agent():
    """
    Create the Dentist Booking Assistant from YAML.
    """

    env = Environment(loader=FileSystemLoader("./prompts"))
    template = env.get_template("instructions.yaml")

    yaml_definition = template.render(
        tools=[
            {"name": "get_all_dentists", "description": "retrieving dentist profiles and details"},
            {"name": "get_free_slots", "description": "getting free available appointment slots"},
            {"name": "book_appointment", "description": "booking a new appointment"},
            {"name": "get_appointment_details", "description": "retrieving details of an existing appointment"},
        ],
        foundry_model=llmconfig.foundry_model,
        foundry_project_endpoint=llmconfig.foundry_project_endpoint,
        default_max_tokens=llmconfig.default_max_tokens,
    )

    factory = AgentFactory(
        client_kwargs={"credential": AzureCliCredential()},
        bindings={
            "get_all_dentists": get_all_dentists,
            "book_appointment": book_appointment,
            "get_free_slots" : get_free_slots,
            "get_appointment_details": get_appointment_details,
            },
    )

    agent = factory.create_agent_from_yaml(yaml_definition)
    agent.id = "booking-assistant"
    agent.middleware = [SecurityAgentMiddleware()]  # Add the security middleware to the agent
    agent.context_providers = [PatientIdProvider(), CurrentDatetimeProvider()]
    return agent


async def main():

    agent = create_booking_agent()

    patient_id = input("Patient Id: ").strip()

    if not patient_id:
        print("Patient id is required.")
        return

    
    session = load_or_create_patient_session(agent, patient_id)
    
    print(f"\nLoaded session for patient: {patient_id}")
    print("Type 'exit' or 'quit' to end the conversation.")
    print("=" * 50)

    try:
        while True:
            user_input = input("User: ").strip()

            if user_input.lower() in ["exit", "quit"]:
                print("Exiting...")
                break

                       
            reasoning_parts = []
            text_parts = []

            async for response_stream in agent.run(
                user_input,
                stream=True,
                session=session,
                options={
                    "reasoning": {
                        "effort": "medium",
                        "summary": "concise",
                    }
                },
            ):
                for content in response_stream.contents:
                    if content.type == "text_reasoning":
                        reasoning_parts.append(content.text)
                    elif content.type == "text":
                        text_parts.append(content.text)

            if reasoning_parts:
                reasoning_text = "".join(reasoning_parts).strip()
                print("\n\nReasoning:")
                print(reasoning_text)

            print("\n\nFinal Answer:")
            print("".join(text_parts).strip())
            print("\n" + "=" * 50 + "\n")

    finally:
        print("Conversation ended.")
        print(f"Session id: {session.service_session_id}")
        save_patient_session(patient_id, session)
        print("Session saved.")

if __name__ == "__main__":
    asyncio.run(main())