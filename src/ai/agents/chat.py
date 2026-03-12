from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from ai.agent_logging import get_agent_logger, log_agent_invocation
from ai.agents.memory_operation import MemoryOperationResult
from config import settings

CHAT_PROMPT = """You are the final response agent for a personal memory assistant.
You will receive:
- The user's latest message batch
- Recent conversation history
- The result of a memory operation that has already been executed

Write the final user-facing reply.

Rules:
- Keep responses concise and natural
- If the operation was save_memory, confirm what was saved in plain language
- If the operation was search_memory, answer using the retrieved memories
- If search returned no memories, say that clearly and briefly
- Do not mention internal pipeline details, routing, or hidden fields"""
CHAT_MODEL = "gpt-4o-mini"
log = get_agent_logger("chat")


def chat(
    message: str,
    operation_result: MemoryOperationResult,
    recent_history: str | None = None,
) -> str:
    """Generate the final reply from a completed memory operation."""
    log_agent_invocation(
        log,
        model=CHAT_MODEL,
        recent_history=recent_history,
        message=message,
        operation_result=operation_result,
    )

    llm = ChatOpenAI(model=CHAT_MODEL, api_key=settings.openai_api_key, temperature=0.7)
    history_block = recent_history or "None"
    operation_block = _format_operation_result(operation_result)
    response = llm.invoke([
        SystemMessage(content=CHAT_PROMPT),
        HumanMessage(
            content=(
                f"Recent history:\n{history_block}\n\n"
                f"Latest user message:\n{message}\n\n"
                f"Memory operation result:\n{operation_block}"
            )
        ),
    ])
    return response.content


def _format_operation_result(operation_result: MemoryOperationResult) -> str:
    if operation_result.operation == "save_memory":
        return (
            "operation: save_memory\n"
            f"saved_content: {operation_result.saved_content}"
        )

    memories = operation_result.memories or []
    if not memories:
        return f"operation: search_memory\nquery: {operation_result.query}\nmemories: none"

    memory_lines = [f"- {memory.content}" for memory in memories]
    return (
        "operation: search_memory\n"
        f"query: {operation_result.query}\n"
        "memories:\n"
        + "\n".join(memory_lines)
    )
