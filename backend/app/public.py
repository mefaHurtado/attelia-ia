from pathlib import Path
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles
from app.main import app as api

DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

frontend = Starlette(routes=[
    Mount("/", app=StaticFiles(directory=str(DIST), html=True))
])

class AtteliaPublica:
    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            return await api(scope, receive, send)

        if scope["type"] == "http" and scope.get("path", "").startswith("/api/"):
            return await api(scope, receive, send)

        return await frontend(scope, receive, send)

app = AtteliaPublica()
