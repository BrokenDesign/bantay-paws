from fastapi import APIRouter, Request

from app.utils.content import load_all_posts, load_post_by_slug
from app.utils.templates import templates

router = APIRouter()


@router.get("/news")
async def news_list(request: Request):
    posts = load_all_posts()
    posts.sort(key=lambda p: p.date, reverse=True)

    return templates.TemplateResponse(
        "news_list.html",
        {
            "request": request,
            "posts": posts,
        },
    )


@router.get("/news/{slug}")
async def news_detail(request: Request, slug: str):
    post = load_post_by_slug(slug)
    return templates.TemplateResponse(
        "news_detail.html",
        {"request": request, "post": post},
    )
