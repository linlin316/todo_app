from pathlib import Path
from app import create_app
from app.extensions import db

app = create_app()

Path(app.instance_path).mkdir(parents=True, exist_ok=True)

with app.app_context():
    db.create_all()

print("✅ DB initialized")