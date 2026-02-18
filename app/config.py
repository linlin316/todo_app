import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev")

    DEFAULT_DB_PATH = (BASE_DIR / ".." / "instance" / "app.db").resolve()
    DEFAULT_DB_URI = "sqlite:///" + DEFAULT_DB_PATH.as_posix()  # ← C:/... 形式

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", DEFAULT_DB_URI)
    SQLALCHEMY_TRACK_MODIFICATIONS = False