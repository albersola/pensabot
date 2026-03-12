import base64
import re

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from openai import OpenAI

from ai.agent_logging import get_agent_logger, log_agent_invocation
from config import settings
from models.message import MessageType
from services.message_pipeline import extract_urls

log = get_agent_logger("media_preprocessing")
IMAGE_DESCRIPTION_MODEL = "gpt-4o"
VOICE_TRANSCRIPTION_MODEL = "whisper-1"
URL_SUMMARY_MODEL = "gpt-4o-mini"
MAX_BODY_CHARS = 15_000
TITLE_PATTERNS = [
    r"<meta[^>]+property=[\"']og:title[\"'][^>]+content=[\"'](.*?)[\"']",
    r"<meta[^>]+name=[\"']title[\"'][^>]+content=[\"'](.*?)[\"']",
    r"<title[^>]*>(.*?)</title>",
]


def transcribe_media(message_type: MessageType, file_url: str) -> str:
    """Convert media to text: voice via Whisper, image via GPT-4o vision."""
    if message_type == MessageType.voice:
        log_agent_invocation(
            log,
            model=VOICE_TRANSCRIPTION_MODEL,
            operation="voice_transcription",
            file_url=file_url,
        )
        client = OpenAI(api_key=settings.openai_api_key)
        with open(file_url, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model=VOICE_TRANSCRIPTION_MODEL,
                file=audio_file,
            )
        log.info("voice_transcribed", file_url=file_url, length=len(transcript.text))
        return transcript.text

    if message_type == MessageType.image:
        with open(file_url, "rb") as image_file:
            image_data = base64.b64encode(image_file.read()).decode("utf-8")

        ext = file_url.rsplit(".", 1)[-1].lower()
        mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"

        log_agent_invocation(
            log,
            model=IMAGE_DESCRIPTION_MODEL,
            file_url=file_url,
            mime=mime,
        )

        llm = ChatOpenAI(model=IMAGE_DESCRIPTION_MODEL, api_key=settings.openai_api_key, temperature=0)
        response = llm.invoke([
            SystemMessage(content="Describe the content of this image in detail. Be concise but complete."),
            HumanMessage(content=[
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_data}"}},
            ]),
        ])
        log.info("image_described", file_url=file_url)
        return response.content

    raise ValueError(f"Unsupported media type: {message_type}")


def scrape_urls(content: str) -> str:
    """Extract and scrape all URLs found in text content."""
    parts: list[str] = []
    for url in extract_urls(content):
        scraped = _scrape_url(url)
        if scraped:
            parts.append(scraped)
    return "\n\n".join(part.strip() for part in parts if part and part.strip())


def _scrape_url(url: str) -> str:
    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        html = response.text

    title = ""
    for pattern in TITLE_PATTERNS:
        match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        if match:
            title = re.sub(r"\s+", " ", match.group(1)).strip()
            break

    body_text = re.sub(r"<script.*?>.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    body_text = re.sub(r"<style.*?>.*?</style>", " ", body_text, flags=re.IGNORECASE | re.DOTALL)
    body_text = re.sub(r"<[^>]+>", " ", body_text)
    body_text = " ".join(body_text.split())

    summary = _summarize_text(body_text[:MAX_BODY_CHARS], url)

    parts = [f"URL: {url}"]
    if title:
        parts.append(f"Title: {title}")
    parts.append(f"Summary: {summary}")

    log.info("url_scraped", url=url, has_title=bool(title), summarized=summary != body_text[:800])
    return "\n".join(parts)


def _summarize_text(text: str, url: str) -> str:
    """Summarize webpage text via LLM. Falls back to excerpt on failure."""
    if not text.strip():
        return ""
    try:
        log_agent_invocation(log, model=URL_SUMMARY_MODEL, operation="url_summarization", url=url)
        llm = ChatOpenAI(model=URL_SUMMARY_MODEL, api_key=settings.openai_api_key, temperature=0)
        response = llm.invoke([
            SystemMessage(content="Summarize this webpage content concisely. Include the main topic, key points, and any important details. Write 2-4 sentences."),
            HumanMessage(content=text),
        ])
        log.info("url_summarized", url=url)
        return response.content
    except Exception:
        log.warning("url_summarization_failed", url=url, exc_info=True)
        return text[:800]
