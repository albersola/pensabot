from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from ai.agent_logging import get_agent_logger, log_agent_invocation
from ai.agents.save_memory import save_memory
from ai.agents.search_memory import search_memory
from ai.agents.chat import chat
from config import settings

log = get_agent_logger("router")
ROUTER_MODEL = "gpt-4o-mini"

ROUTER_PROMPT = """You are a router agent for a personal memory assistant. Given a user message, decide the intent.

Respond with one of these intents:
- "save_memory": The user is sharing information that should be stored, including facts, preferences, plans, notes, links, URL summaries, and extracted media content
- "search_memory": The user wants to recall, retrieve, summarize, or answer something from previously saved memories

Rules:
- You must choose exactly one of: "save_memory" or "search_memory"
- Be generous with save_memory
- If the message is a question asking what is known, remembered, saved, noted, or previously said, choose search_memory
- If the message contains a URL, webpage summary, transcript, image description, or a factual statement to keep for later, choose save_memory
- If the message is ambiguous, default to save_memory unless it is clearly a retrieval request"""


class RouterDecision(BaseModel):
    intent: str = Field(description="One of: save_memory, search_memory")
    reasoning: str = Field(description="Brief explanation of why this intent was chosen")


def route_message(
    user_id: int,
    message: str,
    *,
    recent_history: str | None = None,
) -> str:
    """Route a user message to the appropriate sub-agent and return the response."""
    log_agent_invocation(
        log,
        model=ROUTER_MODEL,
        recent_history=recent_history,
        message=message,
    )

    llm = ChatOpenAI(model=ROUTER_MODEL, api_key=settings.openai_api_key, temperature=0)
    structured_llm = llm.with_structured_output(RouterDecision)

    decision = structured_llm.invoke([
        SystemMessage(content=ROUTER_PROMPT),
        HumanMessage(
            content=(
                f"Recent conversation:\n{recent_history or '(none)'}\n\n"
                f"Latest user batch:\n{message}"
            )
        ),
    ])

    log.info("router_decision", intent=decision.intent, reasoning=decision.reasoning)

    if decision.intent == "search_memory":
        operation_result = search_memory(user_id, message)
    else:
        operation_result = save_memory(
            user_id,
            message,
            recent_history=recent_history,
        )

    return chat(
        message,
        operation_result,
        recent_history=recent_history,
    )
