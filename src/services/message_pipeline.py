import re

from models.message import MessageType

URL_PATTERN = re.compile(r"https?://[^\s<>()]+", re.IGNORECASE)


def extract_urls(text: str) -> list[str]:
    return URL_PATTERN.findall(text or "")


def has_urls(text: str) -> bool:
    return bool(extract_urls(text))


def requires_preprocessing(message_type: MessageType, content: str) -> bool:
    return message_type != MessageType.text or has_urls(content)


def build_effective_content(
    *,
    message_type: MessageType,
    content: str,
    processed_content: str | None,
) -> str:
    raw_text = (content or "").strip()
    derived_text = (processed_content or "").strip()

    if not derived_text:
        return raw_text

    if message_type == MessageType.text:
        if raw_text:
            return f"{raw_text}\n\nURL context:\n{derived_text}"
        return derived_text

    label = "Processed media content"
    if message_type == MessageType.voice:
        label = "Voice transcription"
    elif message_type == MessageType.image:
        label = "Image description"

    if raw_text:
        return f"{raw_text}\n\n{label}:\n{derived_text}"
    return f"{label}:\n{derived_text}"
