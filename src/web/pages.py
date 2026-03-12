from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from auth.dependencies import get_user_id, require_user_id
from config import settings
from db import get_session
from models.external_account import ExternalAccount
from models.message import Message
from redis_client import get_redis
from services.linking import create_link_code

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")

router = APIRouter()


def get_telegram_bot_username() -> str | None:
    username = settings.telegram_bot_username.strip().lstrip("@")
    return username or None


def build_telegram_deep_link(code: str) -> str | None:
    username = get_telegram_bot_username()
    if not username:
        return None
    return f"https://t.me/{username}?start={code}"


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    user_id = get_user_id(request)
    if user_id:
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(request, "index.html", {})


@router.get("/start", response_class=HTMLResponse)
async def start_page(request: Request):
    user_id = get_user_id(request)
    if user_id:
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(
        request,
        "start.html",
        {"telegram_bot_username": get_telegram_bot_username()},
    )


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    user_id: int = Depends(require_user_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(ExternalAccount).where(ExternalAccount.user_id == user_id)
    )
    accounts = result.scalars().all()

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "accounts": accounts,
            "has_accounts": bool(accounts),
            "telegram_bot_username": get_telegram_bot_username(),
        },
    )


@router.get("/messages", response_class=HTMLResponse)
async def messages(
    request: Request,
    user_id: int = Depends(require_user_id),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Message)
        .join(ExternalAccount, Message.external_account_id == ExternalAccount.id)
        .where(ExternalAccount.user_id == user_id)
        .order_by(Message.created_at.desc())
    )
    msgs = result.scalars().all()

    return templates.TemplateResponse(request, "messages.html", {"messages": msgs})


@router.post("/link-telegram", response_class=HTMLResponse)
async def link_telegram(request: Request, user_id: int = Depends(require_user_id)):
    redis = get_redis()
    code = await create_link_code(user_id, redis)
    context = {
        "code": code,
        "start_command": f"/start {code}",
        "telegram_deep_link": build_telegram_deep_link(code),
        "telegram_bot_username": get_telegram_bot_username(),
    }

    if request.headers.get("HX-Request") == "true":
        return templates.TemplateResponse(request, "telegram_link_result.html", context)

    return templates.TemplateResponse(request, "link_telegram.html", context)
