from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

from pensabot.brain import AgentDependencies, brain
from pensabot.models import Chat
from pensabot.storage import Chats, Logs, Memories


async def handle_message(
    text: str,
    user_id: str,
    conversation_id: str,
    chats: Chats,
    memories: Memories,
    logs: Logs,
) -> str:
    """Process a text message independently of its input or output channel."""
    async with chats.conversation(conversation_id):
        recent_messages = await chats.load_recent(conversation_id)
        message_history = _build_message_history(recent_messages)
        result = await brain.run(
            text,
            message_history=message_history,
            deps=AgentDependencies(
                memories=memories,
                logs=logs,
                user_id=user_id,
                conversation_id=conversation_id,
            ),
        )
        await chats.append_exchange(user_id, conversation_id, text, result.output)

    return result.output


def _build_message_history(messages: list[Chat]) -> list[ModelMessage]:
    history: list[ModelMessage] = []
    for message in messages:
        if message.role == "user":
            history.append(ModelRequest(parts=[UserPromptPart(content=message.content)]))
        else:
            history.append(ModelResponse(parts=[TextPart(content=message.content)]))

    return history
