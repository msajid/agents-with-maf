
# Agent-level middleware (applied to ALL runs)
from collections.abc import Awaitable, Callable
from agent_framework import (
    AgentContext,
    AgentMiddleware,
)

class SecurityAgentMiddleware(AgentMiddleware):
    """Agent-level security middleware that validates all requests."""

    async def process(self, context: AgentContext, call_next: Callable[[], Awaitable[None]]) -> None:
        print("[SecurityMiddleware] Checking security for all requests...")

        # Check for security violations in the last user message
        last_message = context.messages[-1] if context.messages else None
        if last_message and last_message.text:
            query = last_message.text.lower()
            if any(word in query for word in ["password", "secret", "credentials"]):
                print("[SecurityMiddleware] Security violation detected! Blocking request.")
                return  # Don't call call_next() to prevent execution

        print("[SecurityMiddleware] Security check passed.")
        context.metadata["security_validated"] = True
        await call_next()