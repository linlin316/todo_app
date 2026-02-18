from datetime import datetime, date
from ..extensions import db


class Task(db.Model):
    """
    タスクモデル。

    プロジェクトに紐づく作業単位。
    カンバン状態管理、優先度、担当者割当、完了日時を保持する。
    """

    __tablename__ = "tasks"

    # ===== 定数（文字列直書き防止） =====
    STATUS_TODO = "todo"
    STATUS_DOING = "doing"
    STATUS_DONE = "done"

    PRIORITY_LOW = "low"
    PRIORITY_MID = "mid"
    PRIORITY_HIGH = "high"

    id = db.Column(db.Integer, primary_key=True)

    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    status = db.Column(
        db.String(20),
        nullable=False,
        default=STATUS_TODO,
        index=True,
    )

    priority = db.Column(
        db.String(20),
        nullable=False,
        default=PRIORITY_MID,
    )

    due_date = db.Column(db.Date, nullable=True)

    assignee_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_by = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    done_at = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # ===== relationships =====
    project = db.relationship("Project", backref="tasks")

    assignee = db.relationship(
        "User",
        foreign_keys=[assignee_id],
    )

    creator = db.relationship(
        "User",
        foreign_keys=[created_by],
    )