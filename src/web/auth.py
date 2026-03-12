from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from auth.passwords import hash_password, verify_password
from db import get_session
from models.user import User

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")

router = APIRouter()


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@router.post("/login")
async def login(request: Request, session: AsyncSession = Depends(get_session)):
    form = await request.form()
    email = form.get("email", "").strip()
    password = form.get("password", "")

    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request, "login.html", {"error": "Invalid email or password"}, status_code=400
        )

    request.scope["session"]["user_id"] = user.id
    return RedirectResponse("/dashboard", status_code=303)


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html")


@router.post("/register")
async def register(request: Request, session: AsyncSession = Depends(get_session)):
    form = await request.form()
    email = form.get("email", "").strip()
    password = form.get("password", "")

    if not email or not password:
        return templates.TemplateResponse(
            request, "register.html", {"error": "Email and password required"}, status_code=400
        )

    existing = await session.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        return templates.TemplateResponse(
            request, "register.html", {"error": "Email already registered"}, status_code=400
        )

    user = User(email=email, password_hash=hash_password(password))
    session.add(user)
    await session.commit()
    await session.refresh(user)

    request.scope["session"]["user_id"] = user.id
    return RedirectResponse("/dashboard", status_code=303)


@router.post("/logout")
async def logout(request: Request):
    request.scope["session"].clear()
    return RedirectResponse("/login", status_code=303)
