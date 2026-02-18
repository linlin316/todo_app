# 📋 Todo App（Flask）

Flask を用いて開発した社内向けタスク／プロジェクト管理システムです。  
プロジェクト単位でメンバー管理・タスク管理・作業記録（ジャーナル）を行うことができます。

---

## 🚀 主な機能

- ユーザー認証（Flask-Login）
- 管理者承認フロー
- プロジェクト管理
- メンバー権限制御（owner / leader / member）
- カンバン形式タスク管理（todo / doing / done）
- 期限・優先度管理
- プロジェクトジャーナル（記録機能）

---

## 🏗️ 技術スタック

- Python 3.x
- Flask
- Flask-Login
- SQLAlchemy
- Jinja2
- SQLite
- HTML / CSS

---

## 🔐 Authentication

本アプリは **Flask-Login によるセッション認証** を採用しています。

### ■ ログインフロー

1. ユーザーが `/login` にアクセス  
2. GET：`auth/login.html` を表示  
3. POST：社員番号 + パスワードで認証  
4. 認証成功時：`login_user(user)` によりログイン状態を生成  
5. 成功後：`home` へリダイレクト  

---

### ■ 認証仕様

- ログインID：`employee_id`（社員番号）
- パスワード：ハッシュ化保存
- セッション管理：Flask-Login
- 未承認ユーザー：ログイン不可
- 停止／ロックユーザー：ログイン不可

---

### ■ 認証必須ページ

以下の画面は `@login_required` により保護されています：

- プロジェクト一覧
- タスク管理
- メンバー管理
- ジャーナル

---

## 🗺️ Route ↔ Template 対応表

| URL | Endpoint | Template |
|-----|----------|----------|
| /login | auth.login | auth/login.html |
| /signup | auth.signup | auth/signup.html |
| /projects/ | projects.list_projects | projects/list.html |
| /projects/<id>/tasks | projects.list_tasks | tasks/list.html |
| /projects/<id>/tasks/create | projects.create_task | tasks/create.html |
| /projects/<id>/members | projects.project_members | projects/members.html |
| /projects/<id>/journal | projects.project_journal | journal/index.html |

---

## 📊 権限モデル

### ■ グローバル権限

- admin
- member

### ■ プロジェクト内権限

- owner
- leader
- member

権限に応じて以下を制御：

- メンバー管理
- タスク操作
- プロジェクトアクセス

---

## 🧪 開発環境セットアップ

リポジトリ取得

```bash
git clone <your-repo-url>
cd todo_app

---

仮想環境作成（推奨）
python -m venv venv
venv\Scripts\activate

---

依存関係インストール
pip install -r requirements.txt

---

データベース
本アプリは SQLite（app.db）を使用しています。

---

起動
python run.py

ブラウザで：
http://localhost:5000
