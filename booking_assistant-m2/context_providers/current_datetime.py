from datetime import datetime
from typing import Any

from agent_framework import AgentSession, ContextProvider, Message, SessionContext


class CurrentDatetimeProvider(ContextProvider):
    def __init__(self) -> None:
        super().__init__("current-datetime")

    async def before_run(
        self,
        *,
        agent: Any,
        session: AgentSession,
        context: SessionContext,
        state: dict[str, Any],
    ) -> None:
        now = datetime.now()
        context.extend_messages(
            self.source_id,
            [Message("system", [f"Current date and time is {now.strftime('%Y-%m-%d %H:%M:%S')}."])],
        )
        print(f"[CurrentDatetimeProvider] Added current datetime {now} to context messages.")

    async def after_run(
        self,
        *,
        agent: Any,
        session: AgentSession,
        context: SessionContext,
        state: dict[str, Any],
    ) -> None:
        pass
