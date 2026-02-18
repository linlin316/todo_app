from flask import render_template, abort
from flask_login import login_required, current_user

from . import admin_bp
from ...models.user import User

def admin_required():
    if not current_user.is_authenticated or current_user.role != "admin":
        abort(403)

@admin_bp.get("/users")
@login_required
def list_users():
    admin_required()
    users = User.query.order_by(User.id.asc()).all()
    return render_template("admin/users.html", users=users)

from flask import request, redirect, url_for, flash
from ...extensions import db


@admin_bp.post("/users/<int:user_id>/role")
@login_required
def change_role(user_id):
    admin_required()

    target = db.session.get(User, user_id)
    if not target:
        abort(404)

    new_role = request.form.get("role")

    if target.role == "admin" and new_role != "admin":
        admin_count = User.query.filter_by(role="admin").count()
        if admin_count <= 1:
            flash("最後のadminは変更できません")
            return redirect(url_for("admin.list_users"))

    target.role = new_role
    db.session.commit()
    return redirect(url_for("admin.list_users"))


@admin_bp.post("/users/<int:user_id>/toggle-active")
@login_required
def toggle_active(user_id):
    admin_required()

    target = db.session.get(User, user_id)
    if not target:
        abort(404)

    if target.id == current_user.id:
        flash("自分自身は停止できません")
        return redirect(url_for("admin.list_users"))

    target.is_active = not target.is_active
    db.session.commit()
    return redirect(url_for("admin.list_users"))

@admin_bp.post("/users/<int:user_id>/approve")
@login_required
def approve_user(user_id):
    admin_required()

    target = db.session.get(User, user_id)
    if not target:
        abort(404)

    # すでに承認済みなら何もしないでもOK
    target.is_approved = True
    target.is_active = True
    target.is_locked = False
    target.failed_login_attempts = 0

    db.session.commit()
    flash("承認しました", "success")
    return redirect(url_for("admin.list_users"))