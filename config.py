import os
from dotenv import load_dotenv
load_dotenv()

def _normalize_db_url(url: str) -> str:
    if url and url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    return url

# Carpeta de runtime segura para escritura en Render
RUNTIME_DB_DIR = os.getenv("RUNTIME_DB_DIR", "/tmp/vetcashflow")
os.makedirs(RUNTIME_DB_DIR, exist_ok=True)
DEFAULT_SQLITE = f"sqlite:///{os.path.join(RUNTIME_DB_DIR, 'app.db')}"

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me")
    SQLALCHEMY_DATABASE_URI = _normalize_db_url(os.getenv("DATABASE_URL", DEFAULT_SQLITE))
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
    ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH")
