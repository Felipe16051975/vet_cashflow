import os
from dotenv import load_dotenv
load_dotenv()

def _normalize_db_url(url: str) -> str:
    if url and url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    return url

def _is_render_environment() -> bool:
    """Check if the app is running on Render platform"""
    return bool(os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID"))

# Carpeta de runtime segura para escritura en Render
RUNTIME_DB_DIR = os.getenv("RUNTIME_DB_DIR", "/tmp/vetcashflow")
os.makedirs(RUNTIME_DB_DIR, exist_ok=True)
DEFAULT_SQLITE = f"sqlite:///{os.path.join(RUNTIME_DB_DIR, 'app.db')}"

def _get_database_uri() -> str:
    """Get the database URI, blocking SQLite in production (Render)"""
    database_url = os.getenv("DATABASE_URL")
    
    if _is_render_environment():
        if not database_url:
            raise RuntimeError(
                "DATABASE_URL is required when running on Render. "
                "SQLite is not allowed in production."
            )
        return _normalize_db_url(database_url)
    
    # Local development: allow fallback to SQLite
    return _normalize_db_url(database_url or DEFAULT_SQLITE)

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
    SQLALCHEMY_DATABASE_URI = _get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
    ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")
