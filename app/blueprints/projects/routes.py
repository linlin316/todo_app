from datetime import datetime, date
from flask import render_template, request, redirect, url_for, current_app, flash, abort
from flask_login import login_required, current_user
from sqlalchemy import case, func
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import SQLAlchemyError
from ...extensions import db
from ...models.project import Project
from ...models.project_member import ProjectMember
from ...models.user import User
from ...models.task import Task

from . import projects_bp
import os, re

def parse_journal_entries(text: str):
    """
    フォーマット例:
    [2026-02-16 14:57] 山田太郎（ID:1001）
    本文...
    """
    entries = []
    if not text:
        return entries

    lines = text.splitlines()
    current = None
    
    header_re = re.compile(
        r'^\[(?P<ts>[\d\-:\s]+)\]\s*(?P<who>.+?)(?:\s*\|\s*task:(?P<task_id>\d+):(?P<task_title>.*))?$'
    )

    for line in lines:
        m = header_re.match(line.strip())
        if m:
            if current:
                current["body"] = "\n".join(current["body"]).strip()
                entries.append(current)
            current = {
                "ts": m.group("ts").strip(),
                "who": (m.group("who") or "").strip(),
                "task_id": int(m.group("task_id")) if m.group("task_id") else None,
                "task_title": (m.group("task_title") or "").strip() if m.group("task_title") else "",
                "body": []
            }
        else:
            if current is not None:
                current["body"].append(line)

    if current:
        current["body"] = "\n".join(current["body"]).strip()
        entries.append(current)

    entries.reverse()
    return entries

def can_access_project(project_id: int) -> bool:
    if current_user.role == "admin":
        return True
    m = ProjectMember.query.filter_by(project_id=project_id, user_id=current_user.id).first()
    return m is not None


def is_project_owner(project_id: int) -> bool:
    if current_user.role == "admin":
        return True
    owner = ProjectMember.query.filter_by(
        project_id=project_id,
        user_id=current_user.id,
        role_in_project="owner"
    ).first()
    return owner is not None


def can_manage_members(project_id: int) -> bool:
    if current_user.role == "admin":
        return True
    if is_project_owner(project_id):
        return True

    pm = ProjectMember.query.filter_by(project_id=project_id, user_id=current_user.id).first()
    return pm is not None and pm.role_in_project == "leader"


@projects_bp.get("/")
@login_required
def list_projects():
    if current_user.role == "admin":
        projects = Project.query.all()
    else:
        projects = (
            db.session.query(Project)
            .join(ProjectMember, Project.id == ProjectMember.project_id)
            .filter(ProjectMember.user_id == current_user.id)
            .all()
        )

    project_ids = [p.id for p in projects]

    # projectごとの status 件数をまとめて取得（N+1回防止）
    stats_rows = []
    if project_ids:
        stats_rows = (
            db.session.query(Task.project_id, Task.status, func.count(Task.id))
            .filter(Task.project_id.in_(project_ids))
            .group_by(Task.project_id, Task.status)
            .all()
        )

    # { project_id: {"todo":0,"doing":0,"done":0} } を作る
    # project が 0 件でも落ちない
    project_stats = {pid: {"todo": 0, "doing": 0, "done": 0} for pid in project_ids}
    for pid, status, cnt in stats_rows:
        if status in ("todo", "doing", "done"):
            project_stats[pid][status] = cnt

    return render_template("projects/list.html", projects=projects, project_stats=project_stats)

@projects_bp.route("/create", methods=["GET", "POST"])
@login_required
def create_project():

    if request.method == "GET":
        return render_template("projects/create.html")

    name = request.form.get("name")
    description = request.form.get("description")

    project = Project(name=name, description=description)
    db.session.add(project)
    db.session.commit()

  
    pm = ProjectMember(project_id=project.id, user_id=current_user.id, role_in_project="owner")
    db.session.add(pm)
    db.session.commit()

    return redirect(url_for("projects.list_projects"))


@projects_bp.route("/<int:project_id>/members", methods=["GET", "POST"])
@login_required
def project_members(project_id):
    project = Project.query.get_or_404(project_id)

    if not can_manage_members(project_id):
        return "権限がありません", 403

    if request.method == "POST":
        employee_id_raw = (request.form.get("employee_id") or "").strip()
        role_in_project = (request.form.get("role_in_project") or "member").strip()

        # roleの安全チェック
        allowed_roles = {"owner", "leader", "member"}
        if role_in_project not in allowed_roles:
            role_in_project = "member"

        # 入力チェック（数字のみ）
        if not employee_id_raw.isdigit():
            flash("社員番号は数字で入力してください", "error")
            return redirect(url_for("projects.project_members", project_id=project_id))

        employee_id = int(employee_id_raw)

        # まず社員番号で探す（絞らない）
        user = User.query.filter_by(employee_id=employee_id).first()
        if user is None:
            flash("その社員番号のユーザーが見つかりません", "error")
            return redirect(url_for("projects.project_members", project_id=project_id))
        
        # 承認チェック
        if hasattr(user, "is_approved") and not user.is_approved:
            flash("このユーザーはまだ承認されていません", "error")
            return redirect(url_for("projects.project_members", project_id=project_id))
        
        # 停止チェック（停止中ユーザーは追加不可）
        if hasattr(user, "is_active") and not user.is_active:
            flash("このユーザーは利用停止中です", "error")
            return redirect(url_for("projects.project_members", project_id=project_id))    
        
        # ロック中なら追加不可
        if hasattr(user, "is_locked") and user.is_locked:
            flash("このユーザーはロックされています", "error")
            return redirect(url_for("projects.project_members", project_id=project_id))

        # もう追加した場合
        exists = ProjectMember.query.filter_by(project_id=project_id, user_id=user.id).first()
        if exists:
            flash("すでにメンバーです", "error")
            return redirect(url_for("projects.project_members", project_id=project_id))
        
        pm = ProjectMember(project_id=project_id, user_id=user.id, role_in_project=role_in_project)
        db.session.add(pm)
        db.session.commit()

        flash("追加しました", "success")
        return redirect(url_for("projects.project_members", project_id=project_id))

    # 一覧表示
    members = ProjectMember.query.filter_by(project_id=project_id).all()
    return render_template("projects/members.html", project=project, members=members, can_manage=can_manage_members(project_id))


@projects_bp.route("/<int:project_id>/members/<int:pm_id>/delete", methods=["POST"])
@login_required
def delete_project_member(project_id, pm_id):
    project = Project.query.get_or_404(project_id)

    if not can_manage_members(project_id):
        return "権限がありません", 403

    # を一緒にロード（pm.user を触って落ちるのを予防）
    pm = (
        ProjectMember.query.options(joinedload(ProjectMember.user))
        .filter_by(id=pm_id, project_id=project_id)
        .first()
    )
    if not pm:
        flash("メンバーが見つかりません（削除済みの可能性があります）", "error")
        return redirect(url_for("projects.project_members", project_id=project_id))

    # 自分を削除できないようにする
    if pm.user_id == current_user.id:
        flash("自分自身は削除できません", "error")
        return redirect(url_for("projects.project_members", project_id=project_id))
    
    if pm.user and pm.user.role == "admin" and current_user.role != "admin":
        flash("管理者ユーザーは削除できません", "error")
        return redirect(url_for("projects.project_members", project_id=project_id))

    # 落ちないように防御的に
    is_global_admin = (current_user.role == "admin")

    me_pm = ProjectMember.query.filter_by(project_id=project_id, user_id=current_user.id).first()
    my_role = me_pm.role_in_project if me_pm else None

    # pm.user が消えてる/存在しないケースも一応ガード
    target_user_role = pm.user.role if getattr(pm, "user", None) else None
    target_role = pm.role_in_project

    # 全体adminは全体admin以外は削除不可
    if target_user_role == "admin" and not is_global_admin:
        flash("管理者ユーザーは削除できません", "error")
        return redirect(url_for("projects.project_members", project_id=project_id))

    # owner 保護（owner 使ってるなら）
    if target_role == "owner" and not is_global_admin:
        flash("オーナーは削除できません", "error")
        return redirect(url_for("projects.project_members", project_id=project_id))

    # leader の範囲制限（owner を消せない等）
    if my_role == "leader" and target_role == "owner":
        flash("リーダー権限ではオーナーを削除できません", "error")
        return redirect(url_for("projects.project_members", project_id=project_id))

    # 実際の削除（失敗しても落とさない）
    try:
        db.session.delete(pm)
        db.session.commit()
        flash("削除しました", "success")
    except SQLAlchemyError as e:
        db.session.rollback()
        flash(f"削除に失敗しました：{e.__class__.__name__}", "error")

    return redirect(url_for("projects.project_members", project_id=project_id))


@projects_bp.route("/<int:project_id>/members/<int:pm_id>/role", methods=["POST"])
@login_required
def update_project_member_role(project_id, pm_id):
    project = Project.query.get_or_404(project_id)

    if not can_manage_members(project_id):
        return "権限がありません", 403

    pm = ProjectMember.query.filter_by(id=pm_id, project_id=project_id).first()
    if not pm:
        flash("メンバーが見つかりません", "error")
        return redirect(url_for("projects.project_members", project_id=project_id))

    new_role = (request.form.get("role_in_project") or "member").strip()

    allowed = {"leader", "member"}
    if new_role not in allowed:
        flash("不正な権限です", "error")
        return redirect(url_for("projects.project_members", project_id=project_id))

    if pm.user_id == current_user.id:
        flash("自分自身の権限は変更できません", "error")
        return redirect(url_for("projects.project_members", project_id=project_id))

    pm.role_in_project = new_role
    db.session.commit()

    flash("権限を変更しました", "success")
    return redirect(url_for("projects.project_members", project_id=project_id))


@projects_bp.get("/<int:project_id>/tasks")
@login_required
def list_tasks(project_id):
    if not can_access_project(project_id):
        return "権限がありません", 403

    project = Project.query.get_or_404(project_id)

    priority_order = case(
    (Task.priority == "high", 0),
    (Task.priority == "mid", 1),
    (Task.priority == "low", 2),
    else_=9
   )
    
    status_order = case(
    (Task.status == "doing", 0),
    (Task.status == "todo", 1),
    (Task.status == "done", 2),
    else_=9
   )
    
    due_null_last = case(
    (Task.due_date.is_(None), 1),
    else_=0
   )
    
    tasks = (Task.query.filter_by(project_id=project_id)
    .order_by(
        status_order.asc(),     # doing → todo → done
        due_null_last.asc(),    # 期限あり → 期限なし
        Task.due_date.asc(),    # 期限が近い順
        priority_order.asc(),   # high → mid → low
        Task.created_at.desc()  # 同条件なら新しい順
     )
    .all()
   )
    return render_template("tasks/list.html", project=project, tasks=tasks, today=date.today())


@projects_bp.route("/<int:project_id>/tasks/create", methods=["GET", "POST"])
@login_required
def create_task(project_id):
    if not can_access_project(project_id):
        return "権限がありません", 403

    project = Project.query.get_or_404(project_id)

    if request.method == "GET":
        return render_template(
            "tasks/create.html",
            project=project,
            today=date.today().isoformat()
        )

    title = (request.form.get("title") or "").strip()
    description = (request.form.get("description") or "").strip()
    priority = request.form.get("priority", "mid")

    due_date_str = (request.form.get("due_date") or "").strip()
    if not due_date_str:
        return render_template(
            "tasks/create.html",
            project=project,
            error="期限は必須です",
            today=date.today().isoformat()
        )

    try:
        due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
    except ValueError:
        return render_template(
            "tasks/create.html",
            project=project,
            error="期限の形式が不正です",
            today=date.today().isoformat()
        )

    # 過去日は不可
    if due_date < date.today():
        return render_template(
            "tasks/create.html",
            project=project,
            error="期限は今日以降を選んでください",
            today=date.today().isoformat()
        )

    task = Task(
        project_id=project_id,
        title=title,
        description=description,
        priority=priority,
        due_date=due_date,
        created_by=current_user.id
    )
    db.session.add(task)
    db.session.commit()

    return redirect(url_for("projects.list_tasks", project_id=project_id))


@projects_bp.post("/<int:project_id>/tasks/<int:task_id>/status")
@login_required
def change_task_status(project_id, task_id):
    if not can_access_project(project_id):
        return "権限がありません", 403

    task = Task.query.filter_by(id=task_id, project_id=project_id).first_or_404()

    action = request.form.get("action")

    if action == "start":
        task.status = "doing"
        task.done_at = None

    elif action == "done":
        task.status = "done"
        task.done_at = datetime.utcnow()

    elif action == "reset":
        task.status = "todo"
        task.done_at = None

    db.session.commit()

    return redirect(url_for("projects.list_tasks", project_id=project_id))


@projects_bp.route("/<int:project_id>/journal", methods=["GET", "POST"])
@login_required
def project_journal(project_id):
    if not can_access_project(project_id):
        return "権限がありません", 403

    project = Project.query.get_or_404(project_id)

    # 保存先フォルダ：instance/journals/
    journal_dir = os.path.join(current_app.instance_path, "journals")
    os.makedirs(journal_dir, exist_ok=True)

    # プロジェクトごとのテキストファイル
    journal_path = os.path.join(journal_dir, f"project_{project_id}.txt")

    def load_text():
        if os.path.exists(journal_path):
            with open(journal_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def build_view(error=None):
        text = load_text()
        entries = parse_journal_entries(text)[:20]  # 最新20件

        grouped = {}
        for e in entries:
            key = e["task_title"] if e["task_id"] else "共通"
            grouped.setdefault(key, []).append(e)

        tasks = Task.query.filter_by(project_id=project_id).order_by(Task.created_at.desc()).all()
        return render_template("journal/index.html", project=project, grouped=grouped, tasks=tasks, error=error)

    if request.method == "POST":
        content = request.form.get("content", "").strip()
        task_id_raw = (request.form.get("task_id") or "").strip()

        if not content:
            return build_view(error="内容を入力してください")

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

        who = current_user.name
        if hasattr(current_user, "employee_id") and current_user.employee_id is not None:
            who = f"{current_user.name}（ID:{current_user.employee_id}）"

        task_part = ""
        if task_id_raw.isdigit():
            task_id = int(task_id_raw)
            t = Task.query.filter_by(id=task_id, project_id=project_id).first()
            if t:
                task_part = f" | task:{t.id}:{t.title}"

        header = f"\n[{now_str}] {who}{task_part}\n"
        body = content + "\n"

        with open(journal_path, "a", encoding="utf-8") as f:
            f.write(header)
            f.write(body)

        return redirect(url_for("projects.project_journal", project_id=project_id))

    # GET
    return build_view()

# 日記の記録を消去する
@projects_bp.post("/<int:project_id>/journal/clear")
@login_required
def clear_project_journal(project_id):

    if current_user.role != "admin":
        return "権限がありません", 403

    project = Project.query.get_or_404(project_id)

    journal_dir = os.path.join(current_app.instance_path, "journals")

    os.makedirs(journal_dir, exist_ok=True)

    journal_path = os.path.join(journal_dir, f"project_{project_id}.txt")

    with open(journal_path, "w", encoding="utf-8") as f:
        f.write("")

    flash("日記を削除しました。", "success")
    return redirect(url_for("projects.project_journal", project_id=project_id))