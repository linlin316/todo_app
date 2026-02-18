from flask import Flask, redirect, url_for, render_template
from flask_login import current_user, login_required
from datetime import timedelta
from sqlalchemy import func
from .config import Config
from .extensions import db, login_manager
from .blueprints.projects import projects_bp


def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)

    app.register_blueprint(projects_bp, url_prefix="/projects")
    
    db.init_app(app)

    login_manager.init_app(app)

    from .models.user import User

    @app.context_processor
    def inject_pending_count():
        if current_user.is_authenticated and current_user.role == "admin":
            pending_count = User.query.filter_by(is_approved=False).count()
        else:
            pending_count = 0
        return dict(pending_count=pending_count)

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))

    login_manager.login_view = "auth.login"

    from .blueprints.auth import auth_bp   
    app.register_blueprint(auth_bp)

    from .blueprints.admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix="/admin")

    @app.get("/dashboard")
    @login_required
    def dashboard():
        from .models.project import Project
        from .models.task import Task
        from .models.user import User
        from .models.project_member import ProjectMember
  
        # プロジェクト数（自分が所属している数）
        my_project_ids = (
            db.session.query(ProjectMember.project_id)
            .filter(ProjectMember.user_id == current_user.id)
            .subquery()
        )
        project_count = db.session.query(func.count()).select_from(my_project_ids).scalar() or 0

        done_values = {"done"}

        all_tasks_in_my_projects = Task.query.filter(Task.project_id.in_(my_project_ids))
        total_task_count = all_tasks_in_my_projects.count()
        open_task_count = all_tasks_in_my_projects.filter(~Task.status.in_(done_values)).count()

        # 承認待ちユーザー数（adminのみ表示）
        pending_user_count = 0
        if current_user.role == "admin" and hasattr(User, "is_approved"):
            pending_user_count = User.query.filter_by(is_approved=False).count()

        return render_template(
            "dashboard.html",
            project_count=project_count,
            total_task_count=total_task_count,
            open_task_count=open_task_count,
            pending_user_count=pending_user_count,
        )

    @app.get("/")
    def home():
        if current_user.is_authenticated:
            return redirect(url_for("projects.list_projects"))
        return redirect(url_for("auth.login"))
    
    @app.template_filter("jst")
    def to_jst(dt):
        if dt is None:
            return ""
        return (dt + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M")

    return app