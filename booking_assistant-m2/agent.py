"""
Dentist Booking Assistant Agent

AI-powered assistant for finding dentists and booking appointments.

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
    cancel_booking,
    reschedule_appointment,
    escalate_to_human,
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

    patient_profile = STORE.get_patient_profile(patient_id)

    if not patient_profile:
        raise ValueError(f"No patient found with id {patient_id}.")

    session_path = STORE.patient_session_path(patient_id)

    if session_path.exists():
        with open(session_path, "r", encoding="utf-8") as file:
            session_dict = json.load(file)

        session = AgentSession.from_dict(session_dict)
    else:
        session = agent.create_session()

    appointments = STORE.get_patient_appointments(patient_id)

    session.state["patient_id"] = patient_id
    session.state["appointments"] = appointments
    session.state["appointment_ids"] = [
        appointment["appointment_id"]
        for appointment in appointments
    ]

    STORE.save_patient_session(patient_id, session.to_dict())

    return session


def create_booking_agent():
    """
    Create the Dentist Booking Assistant from YAML.
    """

    env = Environment(loader=FileSystemLoader("./prompts"))
    template = env.get_template("instructions.yaml")

    yaml_definition = template.render(
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
            "cancel_booking": cancel_booking,
            "reschedule_appointment": reschedule_appointment,
            "escalate_to_human": escalate_to_human,
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

            STORE.save_patient_session(patient_id, session.to_dict())

            if reasoning_parts:
                reasoning_text = "".join(reasoning_parts).strip()
                print("\n\nReasoning:")
                print(reasoning_text)

            print("\n\nFinal Answer:")
            print("".join(text_parts).strip())
            print("\n" + "=" * 50 + "\n")

    finally:
        STORE.save_patient_session(patient_id, session.to_dict())

        print("Conversation ended.")
        print(f"Session id: {session.service_session_id}")


if __name__ == "__main__":
    asyncio.run(main())