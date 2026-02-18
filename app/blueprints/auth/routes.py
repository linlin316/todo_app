from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from werkzeug.security import check_password_hash,generate_password_hash

from . import auth_bp
from ...models.user import User
from ...extensions import db
import re

def is_valid_password(password: str) -> bool:
    has_letter = re.search(r"[A-Za-z]", password)
    has_digit = re.search(r"\d", password)
    long_enough = len(password) >= 6
    return bool(has_letter and has_digit and long_enough)

@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "GET":
        return render_template("auth/signup.html")

    employee_id_str = (request.form.get("employee_id") or "").strip()
    name = (request.form.get("name") or "").strip()
    password = request.form.get("password") or ""

    if not employee_id_str.isdigit():
        return render_template("auth/signup.html", error="社員番号は数字で入力してください")
    if not name:
        return render_template("auth/signup.html", error="名前を入力してください")
    if not is_valid_password(password):
        return render_template(
        "auth/signup.html",
        error="パスワードは英字と数字を含めて8文字以上で入力してください"
    )

    employee_id = int(employee_id_str)

    # 重複チェック
    exists = User.query.filter_by(employee_id=employee_id).first()
    if exists:
        return render_template("auth/signup.html", error="その社員番号はすでに登録されています")

    user = User(
        employee_id=employee_id,
        name=name,
        password_hash=generate_password_hash(password),
        role="member",
        is_active=False,      # 承認待ち
        is_locked=False,
        failed_login_attempts=0,
        is_approved=False,
    )
    db.session.add(user)
    db.session.commit()

    # 申請完了メッセージ
    flash("申請を受け付けました。管理者の承認後にログインできます。", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("auth/login.html")

    employee_id_str = request.form.get("employee_id", "").strip()
    password = request.form.get("password", "")

    # 数字チェック（空や文字を弾く）
    if not employee_id_str.isdigit():
        return render_template("auth/login.html", error="社員番号は数字で入力してください")

    employee_id = int(employee_id_str)

    user = User.query.filter_by(employee_id=employee_id).first()

    if user is None:
        return render_template("auth/login.html", error="ユーザーが見つかりません")

    # 承認チェック（あなたの運用に合わせて）
    if not user.is_approved:
        return render_template("auth/login.html", error="承認待ちです。管理者の承認後にログインできます")

    # 停止・ロックなど（あるなら）
    if not user.is_active:
        return render_template("auth/login.html", error="アカウントは停止中です。管理者に連絡してください")

    if user.is_locked:
        return render_template("auth/login.html", error="アカウントがロックされています。管理者に連絡してください")

    if not check_password_hash(user.password_hash, password):
        return render_template("auth/login.html", error="パスワードが違います")

    login_user(user)
    return redirect(url_for("home"))

@auth_bp.get("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))