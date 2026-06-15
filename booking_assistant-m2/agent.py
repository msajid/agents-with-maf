"""
Dentist Booking Assistant Agent

Usage:
python agent.py
"""

import asyncio
import json

from agent_framework import AgentSession
from agent_framework.declarative import AgentFactory
from azure.identity import AzureCliCredential
from jinja2 import Environment, FileSystemLoader
from azure.monitor.opentelemetry import configure_azure_monitor
from agent_framework.observability import create_resource, enable_instrumentation

from llm_config import LLMProviderConfig
from tools import (
    STORE,
    get_all_dentists,
    lookup_patient,
    search_available_slots,
    book_appointment,
    get_appointment_details,
)


llmconfig = LLMProviderConfig()


if llmconfig.application_insights_connection_string:
    configure_azure_monitor(
        connection_string=llmconfig.application_insights_connection_string,
        resource=create_resource(),
        enable_live_metrics=True,
    )

    enable_instrumentation(enable_sensitive_data=True)


def refresh_session_state(
    session: AgentSession,
    patient_id: str,
) -> None:
    """
    Refresh session state from patient files.

    This is called once at startup and once at the end.
    """

    appointments = STORE.get_patient_appointments(patient_id)

    session.state["patient_id"] = patient_id
    session.state["appointments"] = appointments
    session.state["appointment_ids"] = [
        appointment["appointment_id"]
        for appointment in appointments
    ]


def load_or_create_patient_session(agent, patient_id: str) -> AgentSession:
    patient = STORE.get_patient_profile(patient_id)

    if not patient:
        raise ValueError(f"No patient found with id {patient_id}.")

    session_path = STORE.patient_session_path(patient_id)

    if session_path.exists():
        with open(session_path, "r", encoding="utf-8") as file:
            session_dict = json.load(file)

        session = AgentSession.from_dict(session_dict)
    else:
        session = agent.create_session()

    refresh_session_state(session, patient_id)

    return session


def create_booking_agent():
    env = Environment(loader=FileSystemLoader("./prompts"))
    template = env.get_template("instructions.yaml")

    yaml_definition = template.render(
        tools=[
            {
                "name": "get_all_dentists",
                "description": "retrieving dentist profiles and details",
            },
            {
                "name": "lookup_patient",
                "description": "looking up patient records and saved appointments",
            },
            {
                "name": "search_available_slots",
                "description": "searching for available appointment slots",
            },
            {
                "name": "book_appointment",
                "description": "booking a new appointment",
            },
            {
                "name": "get_appointment_details",
                "description": "retrieving details for a booked appointment",
            },
        ],
        foundry_model=llmconfig.foundry_model,
        foundry_project_endpoint=llmconfig.foundry_project_endpoint,
        default_max_tokens=llmconfig.default_max_tokens,
    )

    factory = AgentFactory(
        client_kwargs={"credential": AzureCliCredential()},
        bindings={
            "get_all_dentists": get_all_dentists,
            "lookup_patient": lookup_patient,
            "search_available_slots": search_available_slots,
            "book_appointment": book_appointment,
            "get_appointment_details": get_appointment_details,
        },
    )

    agent = factory.create_agent_from_yaml(yaml_definition)
    agent.id = "booking-assistant"

    return agent


async def main():
    STORE.bootstrap()

    agent = create_booking_agent()

    patient_id = input("Patient Id: ").strip()

    if not patient_id:
        print("Patient id is required for this demo.")
        return

    try:
        session = load_or_create_patient_session(agent, patient_id)
    except ValueError as error:
        print(error)
        return

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

            agent_input = f"""
                            Current patient context:
                            - patient_id: {patient_id}

                            When the user says "my", "me", or "my profile", use this patient id.
                            Do not ask for the patient id again unless it is missing.

                            User request:
                            {user_input}
                            """
            
            async for response_stream in agent.run(
                agent_input,
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
                print("\n\nReasoning:")
                print("".join(reasoning_parts).strip())

            print("\n\nFinal Answer:")
            print("".join(text_parts).strip())
            print("\n" + "=" * 50 + "\n")

    finally:
        refresh_session_state(session, patient_id)
        STORE.save_patient_session(patient_id, session.to_dict())

        print("Conversation ended.")
        print(f"Session id: {session.service_session_id}")


if __name__ == "__main__":
    asyncio.run(main())