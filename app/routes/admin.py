import os
import re
import unicodedata
from pathlib import Path

from fastapi import (
    APIRouter,
    File,
    Form,
    Request,
    UploadFile,
)
from fastapi.responses import RedirectResponse
from app.utils.auth import authenticate, is_admin_authenticated
from app.utils.content import (
    delete_post_by_slug,
    load_all_posts,
    load_post_by_slug,
    update_post_file,
    write_post_file,
)
from app.utils.templates import templates

BASE_DIR = Path(__file__).resolve().parents[2]
CONTENT_DIR = BASE_DIR / "content"
MEDIA_DIR = CONTENT_DIR / "media"

router = APIRouter(prefix="/admin", tags=["admin"])


def append_images_markdown(body: str, image_paths: list[str]) -> str:
    """Append markdown image references for any paths not already present in the body."""
    if not image_paths:
        return body

    existing = {path for path in image_paths if path in body}
    new_refs = [f"[![Rescue photo]({path})]({path})" for path in image_paths if path not in existing]
    if not new_refs:
        return body

    cleaned = body.strip()
    if cleaned:
        return f"{cleaned}\n\n" + "\n".join(new_refs) + "\n"
    return "\n".join(new_refs) + "\n"


def slugify(title: str) -> str:
    value = (
        unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode("ascii")
    )
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value)
    value = value.strip("-")
    return value.lower()


def require_admin(request: Request):
    if not is_admin_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)


@router.get("/login")
async def login_form(request: Request):
    if is_admin_authenticated(request):
        return RedirectResponse(url="/admin/posts", status_code=303)
    return templates.TemplateResponse("admin_login.html", {"request": request})


@router.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    if authenticate(username, password):
        request.session["is_admin"] = True
        return RedirectResponse(url="/admin/posts", status_code=303)

    return templates.TemplateResponse(
        "admin_login.html",
        {
            "request": request,
            "error": "Invalid credentials",
        },
        status_code=401,
    )


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=303)


@router.get("/posts")
async def admin_posts(request: Request):
    if not is_admin_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    posts = load_all_posts()
    return templates.TemplateResponse(
        "admin_posts_list.html", {"request": request, "posts": posts}
    )


@router.get("/posts/new")
async def new_post_form(request: Request):
    if not is_admin_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    return templates.TemplateResponse("admin_new_post.html", {"request": request})


@router.post("/posts/new")
async def new_post_submit(
    request: Request,
    title: str = Form(...),
    slug: str = Form(""),
    body: str = Form(...),
    images: list[UploadFile] = File(default_factory=list),
):
    if not is_admin_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    if not slug:
        slug = slugify(title)

    # Save images under content/media/{slug}/
    saved_images: list[str] = []
    if images:
        target_dir = MEDIA_DIR / slug
        target_dir.mkdir(parents=True, exist_ok=True)
        for img in images:
            filename = img.filename or "image"
            dest = target_dir / filename
            with dest.open("wb") as f:
                f.write(await img.read())
            # path to use in markdown: /media/{slug}/{filename}
            saved_images.append(f"/media/{slug}/{filename}")

    body_with_images = append_images_markdown(body, saved_images)
    write_post_file(
        title=title,
        slug=slug,
        body=body_with_images,
        author=os.getenv("ADMIN_USERNAME", "admin"),
    )

    return templates.TemplateResponse(
        "admin_new_post.html",
        {
            "request": request,
            "success": True,
            "saved_images": saved_images,
            "slug": slug,
        },
    )


@router.post("/generate-slug")
async def generate_slug(request: Request):
    form = await request.form()
    title = form.get("title", "")
    slug = slugify(title)  # type: ignore

    return templates.TemplateResponse(
        "partials/slug_field.html", {"request": request, "slug": slug}
    )


@router.get("/posts/{slug}/edit")
async def edit_post_form(request: Request, slug: str):
    if not is_admin_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    post = load_post_by_slug(slug)
    if post is None:
        return RedirectResponse(url="/admin/posts", status_code=303)

    return templates.TemplateResponse(
        "admin_edit_post.html",
        {"request": request, "post": post},
    )


@router.post("/posts/{slug}/edit")
async def edit_post_submit(
    request: Request,
    slug: str,
    title: str = Form(...),
    new_slug: str = Form(""),
    body: str = Form(...),
    images: list[UploadFile] = File(default_factory=list),
):
    if not is_admin_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    target_slug = new_slug or slug

    # Prepare image paths to append to markdown
    saved_images: list[str] = []
    image_targets: list[tuple[UploadFile, Path, str]] = []
    if images:
        for img in images:
            filename = img.filename or "image"
            dest = MEDIA_DIR / target_slug / filename
            image_targets.append((img, dest, f"/media/{target_slug}/{filename}"))
            saved_images.append(f"/media/{target_slug}/{filename}")

    body_with_images = append_images_markdown(body, saved_images)

    try:
        update_post_file(
            existing_slug=slug,
            title=title,
            slug=target_slug,
            body=body_with_images,
            author=os.getenv("ADMIN_USERNAME", "admin"),
        )
    except ValueError:
        return RedirectResponse(url="/admin/posts", status_code=303)

    # Save images after possible slug rename to avoid directory conflicts
    if image_targets:
        target_dir = MEDIA_DIR / target_slug
        target_dir.mkdir(parents=True, exist_ok=True)
        for img, dest, _ in image_targets:
            with dest.open("wb") as f:
                f.write(await img.read())

    return templates.TemplateResponse(
        "admin_edit_post.html",
        {
            "request": request,
            "post": load_post_by_slug(target_slug),
            "success": True,
            "saved_images": saved_images,
            "slug": target_slug,
        },
    )


@router.post("/posts/{slug}/delete")
async def delete_post(slug: str, request: Request):
    if not is_admin_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    try:
        delete_post_by_slug(slug, delete_media=True)
    except ValueError:
        pass

    return RedirectResponse(url="/admin/posts", status_code=303)
