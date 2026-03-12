from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from pydantic import BaseModel, Field

from ai.agent_logging import get_agent_logger, log_agent_invocation, snapshot_context
from ai.agents.memory_operation import SavedMemoryResult
from config import settings
from db_sync import SyncSessionLocal
from models.memory import Memory

log = get_agent_logger("save_memory")
SAVE_MEMORY_MODEL = "gpt-4o"

EXTRACT_PROMPT = """You are a memory extraction agent. Given a user message, extract the core information to remember (clean, concise version).

Examples:
- "Remember that my dentist appointment is on March 15" → "Dentist appointment on March 15"
- "My favorite color is blue" → "Favorite color is blue"

Use the recent conversation context only to disambiguate references like "the usual place" or "that project". Do not save the whole conversation, only the new memory the user is expressing now."""


class ExtractedMemory(BaseModel):
    content: str = Field(description="The core information to remember")


def save_memory(
    user_id: int,
    message: str,
    recent_history: str | None = None,
) -> SavedMemoryResult:
    """Extract memory from message, generate embedding, and save to DB."""
    log_agent_invocation(
        log,
        model=SAVE_MEMORY_MODEL,
        recent_history=recent_history,
        message=message,
    )

    llm = ChatOpenAI(model=SAVE_MEMORY_MODEL, api_key=settings.openai_api_key, temperature=0)
    structured_llm = llm.with_structured_output(ExtractedMemory)

    extracted = structured_llm.invoke([
        SystemMessage(content=EXTRACT_PROMPT),
        HumanMessage(
            content=(
                f"Recent conversation:\n{recent_history or '(none)'}\n\n"
                f"User batch:\n{message}"
            )
        ),
    ])

    log.info(
        "memory_embedding_requested",
        model=settings.embedding_model,
        agent_context=snapshot_context(
            extracted_content=extracted.content,
        ),
    )

    embeddings = OpenAIEmbeddings(
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
        api_key=settings.openai_api_key,
    )
    vector = embeddings.embed_query(extracted.content)

    memory = Memory(
        user_id=user_id,
        content=extracted.content,
        embedding=vector,
    )

    with SyncSessionLocal() as session:
        session.add(memory)
        session.commit()
        log.info("memory_saved", memory_id=memory.id, user_id=user_id)

    return SavedMemoryResult(saved_content=extracted.content)
