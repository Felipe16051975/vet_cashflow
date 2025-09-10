import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    SQLITE_PATH = os.path.join(BASE_DIR, "instance", "cashflow.db")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{SQLITE_PATH}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv("SECRET_KEY", "pon-un-secreto-largo-aqui")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")  # o ADMIN_PASSWORD_HASH
