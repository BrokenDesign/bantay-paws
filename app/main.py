import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.routes import admin, news
from app.utils.content import load_story
from app.utils.templates import templates

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

app = FastAPI()

# Session middleware for simple login
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "change-me"),
    session_cookie="nonprofit_session",
)

# Static files
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/media", StaticFiles(directory=BASE_DIR / "content" / "media"), name="media")

# Routers
app.include_router(news.router)
app.include_router(admin.router)


@app.get("/", include_in_schema=False)
async def root(request: Request):
    return templates.TemplateResponse(
        "donate.html",
        {"request": request},
    )


@app.get("/story", include_in_schema=False)
async def story(request: Request):
    story = load_story()
    return templates.TemplateResponse(
        "story.html",
        {
          "request": request,
          "story": story,
        },
    )
