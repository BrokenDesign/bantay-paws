from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import markdown as md
import yaml

BASE_DIR = Path(__file__).resolve().parents[2]
CONTENT_DIR = BASE_DIR / "content"
POSTS_DIR = CONTENT_DIR / "posts"


@dataclass
class PostMeta:
    title: str
    slug: str
    date: datetime
    author: str | None
    filepath: Path


@dataclass
class Post:
    title: str
    slug: str
    date: datetime
    body_html: str
    raw_body: Optional[str] = None
    path: Optional[Path] = None
    author: Optional[str] = None


def parse_post_file(path: Path) -> tuple[PostMeta, str, str]:
    """Parse a markdown file with YAML front matter, returning metadata, raw markdown, and HTML."""
    text = path.read_text(encoding="utf-8")

    if text.startswith("---"):
        _, fm, body = text.split("---", 2)
        front = yaml.safe_load(fm) or {}
        raw_body = body.strip()
    else:
        front = {}
        raw_body = text.strip()

    title = front.get("title", path.stem)
    slug = front.get("slug", path.stem)
    date_str = front.get("date")
    author = front.get("author")

    if date_str:
        if isinstance(date_str, datetime):
            date = date_str
        else:
            date = datetime.fromisoformat(str(date_str))
    else:
        try:
            prefix, *_ = path.stem.split("-", 3)
            date = datetime.fromisoformat(prefix)
        except Exception:
            date = datetime.now()

    meta = PostMeta(
        title=title,
        slug=slug,
        date=date,
        author=author,
        filepath=path,
    )

    html = md.markdown(raw_body, extensions=["fenced_code", "tables"])
    return meta, raw_body, html


def load_all_posts() -> list[Post]:
    posts = []
    for path in POSTS_DIR.glob("*.md"):
        meta, raw_body, html = parse_post_file(path)

        posts.append(
            Post(
                title=meta.title,
                slug=meta.slug,
                date=meta.date,
                body_html=html,
                raw_body=raw_body,
                path=path,
                author=meta.author,
            )
        )
    return posts


def load_post_by_slug(slug: str) -> Post | None:
    for path in POSTS_DIR.glob("*.md"):
        meta, raw_body, html = parse_post_file(path)
        if meta.slug == slug:
            return Post(
                title=meta.title,
                slug=meta.slug,
                date=meta.date,
                body_html=html,
                raw_body=raw_body,
                path=path,
                author=meta.author,
            )
    return None


def load_story() -> Post | None:
    path = CONTENT_DIR / "story.md"
    if not path.exists():
        return None

    meta, raw_body, html = parse_post_file(path)
    return Post(
        title=meta.title,
        slug=meta.slug,
        date=meta.date,
        body_html=html,
        raw_body=raw_body,
        path=path,
        author=meta.author,
    )


def write_post_file(
    title: str,
    slug: str,
    body: str,
    author: str | None = None,
    date: datetime | None = None,
) -> Path:
    if date is None:
        date = datetime.now()

    POSTS_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"{date.date().isoformat()}-{slug}.md"
    path = POSTS_DIR / filename

    front_matter = {
        "title": title,
        "slug": slug,
        "date": date.isoformat(),
    }
    if author:
        front_matter["author"] = author

    fm_yaml = yaml.safe_dump(front_matter, sort_keys=False).strip()

    content = f"---\n{fm_yaml}\n---\n\n{body.strip()}\n"
    path.write_text(content, encoding="utf-8")
    return path


def update_post_file(
    existing_slug: str,
    title: str,
    slug: str,
    body: str,
    author: str | None = None,
) -> Path:
    post = load_post_by_slug(existing_slug)
    if post is None or post.path is None:
        raise ValueError("Post not found")

    target_slug = slug or existing_slug
    date = post.date
    author = author or post.author

    new_filename = f"{date.date().isoformat()}-{target_slug}.md"
    new_path = POSTS_DIR / new_filename

    # Avoid clobbering another post if the new slug already exists
    if new_path.exists() and new_path != post.path:
        raise ValueError("Target slug already exists")

    POSTS_DIR.mkdir(parents=True, exist_ok=True)

    front_matter = {
        "title": title,
        "slug": target_slug,
        "date": date.isoformat(),
    }
    if author:
        front_matter["author"] = author

    fm_yaml = yaml.safe_dump(front_matter, sort_keys=False).strip()
    content = f"---\n{fm_yaml}\n---\n\n{body.strip()}\n"

    new_path.write_text(content, encoding="utf-8")

    if new_path != post.path:
        post.path.unlink(missing_ok=True)

    old_media_dir = CONTENT_DIR / "media" / existing_slug
    new_media_dir = CONTENT_DIR / "media" / target_slug
    if target_slug != existing_slug and old_media_dir.exists():
        new_media_dir.parent.mkdir(parents=True, exist_ok=True)
        old_media_dir.rename(new_media_dir)

    return new_path


def delete_post_by_slug(slug: str, delete_media: bool = True) -> None:
    post = load_post_by_slug(slug)
    if post is None or post.path is None:
        raise ValueError("Post not found")

    post.path.unlink(missing_ok=True)

    if delete_media:
        media_dir = CONTENT_DIR / "media" / slug
        if media_dir.exists():
            import shutil

            shutil.rmtree(media_dir)
