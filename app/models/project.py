from datetime import datetime
from ..extensions import db


class Project(db.Model):
    """
    プロジェクトモデル。

    タスク管理・メンバー管理の単位となるエンティティ。
    論理削除（アーカイブ）に対応。

    Attributes:
        id (int): 主キー
        name (str): プロジェクト名
        description (str | None): プロジェクト説明
        is_archived (bool): アーカイブ状態
        created_at (datetime): 作成日時（UTC）
    """

    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(150),
        nullable=False,
        index=True,  # 検索・一覧表示の最適化
    )

    description = db.Column(db.Text, nullable=True)

    # 論理削除フラグ
    is_archived = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
    )

    # 作成日時（UTC）
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )