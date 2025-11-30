import os

from fastapi import Request


def is_admin_authenticated(request: Request) -> bool:
    return bool(request.session.get("is_admin"))


def authenticate(username: str, password: str) -> bool:
    admin_user = os.getenv("ADMIN_USERNAME", "admin")
    admin_pass = os.getenv("ADMIN_PASSWORD", "changeme")
    return username == admin_user and password == admin_pass
