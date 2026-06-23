from typing import Any

from agent_framework import AgentSession, ContextProvider, SessionContext


class PatientIdProvider(ContextProvider):
    def __init__(self) -> None:
        super().__init__("patient-id")

    async def before_run(
        self,
        *,
        agent: Any,
        session: AgentSession,
        context: SessionContext,
        state: dict[str, Any],
    ) -> None:
        if patient_id := session.state.get("patient_id"):
            context.extend_instructions(self.source_id, f"User's patient ID is {patient_id}.")
            print(f"[PatientIdProvider] Added patient ID {patient_id} to context instructions.")

    async def after_run(
        self,
        *,
        agent: Any,
        session: AgentSession,
        context: SessionContext,
        state: dict[str, Any],
    ) -> None:
        pass
