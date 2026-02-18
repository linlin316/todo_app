from ..extensions import db


class ProjectMember(db.Model):
    """
    プロジェクトメンバー関連テーブル。

    ユーザーとプロジェクトの多対多関係を管理し、
    プロジェクト単位の権限(role_in_project)を保持する。

    制約:
        - 同一ユーザーが同一プロジェクトに重複登録されない
    """

    __tablename__ = "project_members"

    __table_args__ = (
        db.UniqueConstraint(
            "project_id",
            "user_id",
            name="uq_project_user",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)

    project_id = db.Column(
        db.Integer,
        db.ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    role_in_project = db.Column(
        db.String(20),
        nullable=False,
        default="member",
    )

    # relationships
    user = db.relationship(
        "User",
        backref=db.backref("project_memberships", lazy="dynamic"),
    )

    project = db.relationship(
        "Project",
        backref=db.backref("memberships", lazy="dynamic"),
    )