from datetime import datetime
from pathlib import Path

from fastapi.templating import Jinja2Templates


BASE_DIR = Path(__file__).resolve().parents[2]

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Shared globals for all templates
templates.env.globals["current_year"] = datetime.utcnow().year
