import json
import uuid

from itsdangerous import BadSignature, URLSafeSerializer
from starlette.datastructures import MutableHeaders
from starlette.requests import HTTPConnection
from starlette.types import ASGIApp, Message, Receive, Scope, Send

SESSION_TTL = 86400  # 24 hours
COOKIE_NAME = "session_id"


class SessionData(dict):
    modified: bool = False

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.modified = True

    def __delitem__(self, key):
        super().__delitem__(key)
        self.modified = True

    def clear(self):
        super().clear()
        self.modified = True


class RedisSessionMiddleware:
    def __init__(self, app: ASGIApp, secret_key: str, get_redis=None):
        self.app = app
        self._get_redis = get_redis
        self.serializer = URLSafeSerializer(secret_key)
        self.cookie_name = COOKIE_NAME

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        conn = HTTPConnection(scope)
        session_id = self._get_session_id(conn)
        session = SessionData()

        if session_id:
            data = await self._get_redis().get(f"session:{session_id}")
            if data:
                session.update(json.loads(data))
                session.modified = False

        scope["state"] = getattr(scope.get("state"), "__dict__", {}) if "state" not in scope else scope["state"]
        if not hasattr(scope, "state"):
            scope.setdefault("state", {})
        scope["session"] = session

        async def send_wrapper(message: Message):
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                if session.modified or (not session_id and session):
                    new_id = session_id or uuid.uuid4().hex
                    await self._get_redis().set(
                        f"session:{new_id}",
                        json.dumps(dict(session)),
                        ex=SESSION_TTL,
                    )
                    signed = self.serializer.dumps(new_id)
                    headers.append(
                        "set-cookie",
                        f"{self.cookie_name}={signed}; Path=/; HttpOnly; SameSite=Lax; Max-Age={SESSION_TTL}",
                    )
                elif session_id and not session:
                    await self._get_redis().delete(f"session:{session_id}")
                    headers.append(
                        "set-cookie",
                        f"{self.cookie_name}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0",
                    )
            await send(message)

        await self.app(scope, receive, send_wrapper)

    def _get_session_id(self, conn: HTTPConnection) -> str | None:
        cookie = conn.cookies.get(self.cookie_name)
        if not cookie:
            return None
        try:
            return self.serializer.loads(cookie)
        except BadSignature:
            return None
