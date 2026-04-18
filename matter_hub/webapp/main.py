from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from matter_hub.webapp import routes

BASE_DIR = Path(__file__).parent
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def create_app() -> FastAPI:
    app = FastAPI(title="Matter Hub")
    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
    app.state.templates = TEMPLATES
    app.include_router(routes.router)
    return app


app = create_app()
