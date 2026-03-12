from dataclasses import dataclass
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from ai.agent_logging import get_agent_logger, log_agent_invocation
from config import settings

log = get_agent_logger("intake")
INTAKE_MODEL = "gpt-4o-mini"

INTAKE_PROMPT = """You are the intake agent that decides whether the assistant should act now or ask for clarification.

You will receive:
- The latest batch of pending user messages for one chat
- A short recent conversation history
- The current wait attempt count

Choose exactly one action:
- "proceed": there is enough information to hand off the batch to the router
- "wait": the user message likely continues in another imminent message and it is better to wait briefly
- "ask_user": there is not enough information and the assistant should ask a focused follow-up question

Rules:
- Very short fragments, unfinished clauses, trailing conjunctions, or abrupt cut-offs should usually become "wait"
- If the wait attempt count has reached the max, do not choose "wait"
- If the user already gave enough detail, choose "proceed"
- Follow-up questions must be short and specific
"""


class IntakeDecision(BaseModel):
    action: Literal["proceed", "wait", "ask_user"] = Field(description="One of: proceed, wait, ask_user")
    reasoning: str = Field(description="Brief explanation of the decision")
    question: str | None = Field(default=None, description="Question to ask if action is ask_user")


@dataclass
class IntakeResult:
    action: Literal["proceed", "wait", "ask_user"]
    reasoning: str
    question: str | None = None


def decide_intake_action(
    *,
    pending_batch: str,
    recent_history: str,
    wait_attempt: int,
    max_wait_attempts: int,
) -> IntakeResult:
    decision = _invoke_intake_model(
        pending_batch=pending_batch,
        recent_history=recent_history,
        wait_attempt=wait_attempt,
        max_wait_attempts=max_wait_attempts,
    )

    log.info("intake_decision", action=decision.action, reasoning=decision.reasoning)

    return IntakeResult(
        action=decision.action,
        reasoning=decision.reasoning,
        question=decision.question,
    )


def _invoke_intake_model(
    *,
    pending_batch: str,
    recent_history: str,
    wait_attempt: int,
    max_wait_attempts: int,
) -> IntakeDecision:
    log_agent_invocation(
        log,
        model=INTAKE_MODEL,
        pending_batch=pending_batch,
        recent_history=recent_history,
        wait_attempt=wait_attempt,
        max_wait_attempts=max_wait_attempts,
    )

    llm = ChatOpenAI(model=INTAKE_MODEL, api_key=settings.openai_api_key, temperature=0)
    structured_llm = llm.with_structured_output(IntakeDecision)

    return structured_llm.invoke([
        SystemMessage(content=INTAKE_PROMPT),
        HumanMessage(
            content=(
                f"Pending batch:\n{pending_batch or '(empty)'}\n\n"
                f"Recent history:\n{recent_history or '(none)'}\n\n"
                f"Wait attempt: {wait_attempt}\n"
                f"Max wait attempts: {max_wait_attempts}"
            )
        ),
    ])
