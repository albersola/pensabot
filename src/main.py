import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from auth.sessions import RedisSessionMiddleware
from config import settings
from providers.telegram import TelegramProvider
from redis_client import close_redis, get_redis, init_redis
from web.auth import router as auth_router
from web.pages import router as pages_router

log = structlog.get_logger()
BASE_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_redis()

    telegram = TelegramProvider(settings.telegram_bot_token)
    app.state.telegram_provider = telegram

    if settings.telegram_bot_token:
        asyncio.create_task(telegram.start_polling())

    log.info("app_started", telegram_enabled=bool(settings.telegram_bot_token))
    yield

    await telegram.close()
    await close_redis()


app = FastAPI(title="pensabot", lifespan=lifespan)
app.add_middleware(RedisSessionMiddleware, secret_key=settings.secret_key, get_redis=get_redis)
app.mount("/static", StaticFiles(directory=BASE_DIR / "web" / "static"), name="static")
Path(settings.media_dir).mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")

app.include_router(auth_router)
app.include_router(pages_router)
