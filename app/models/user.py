from datetime import datetime
from flask_login import UserMixin
from app.extensions import db


class User(db.Model, UserMixin):
    """
    ユーザーモデル。

    社員番号(employee_id)でログイン管理を行う。
    管理者承認フロー、アカウントロック、権限制御に対応。

    Attributes:
        id (int): 主キー
        employee_id (int): 社員番号（ログインID）
        name (str): ユーザー名
        password_hash (str): ハッシュ化パスワード
        role (str): 権限（admin / leader / member）
        is_active (bool): アカウント有効フラグ
        failed_login_attempts (int): ログイン失敗回数
        is_locked (bool): ロック状態
        created_at (datetime): 作成日時（UTC）
        is_approved (bool): 管理者承認済みフラグ
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    # ログインID（社員番号）
    employee_id = db.Column(
        db.Integer,
        unique=True,
        nullable=False,
        index=True,
    )

    name = db.Column(db.String(100), nullable=False)

    password_hash = db.Column(db.String(255), nullable=False)

    # 権限：admin / leader / member
    role = db.Column(db.String(20), nullable=False, default="member")

    # アカウント状態
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    # ログイン失敗管理
    failed_login_attempts = db.Column(db.Integer, nullable=False, default=0)
    is_locked = db.Column(db.Boolean, nullable=False, default=False)

    # 作成日時（UTC）
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    # 管理者承認フラグ
    is_approved = db.Column(db.Boolean, nullable=False, default=False)