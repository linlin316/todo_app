from app import create_app
from app.extensions import db
from app.models.user import User
from werkzeug.security import generate_password_hash

app = create_app()

ADMIN_EMPLOYEE_ID = 9999
ADMIN_NAME = "管理者"
ADMIN_PASSWORD = "kanri9999"

with app.app_context():

    exists = User.query.filter_by(employee_id=ADMIN_EMPLOYEE_ID).first()
    if exists:
        print("Admin already exists.")
    else:
        admin = User(
            employee_id=ADMIN_EMPLOYEE_ID,
            name=ADMIN_NAME,
            password_hash=generate_password_hash(ADMIN_PASSWORD),
            role="admin",
            is_active=True,
            is_approved=True,
            is_locked=False,
            failed_login_attempts=0,
        )
        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully!")