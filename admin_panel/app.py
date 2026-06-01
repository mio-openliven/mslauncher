from __future__ import annotations

import shutil
import tempfile
import hashlib
import hmac
from pathlib import Path
from sqlite3 import Row
from typing import Annotated

import uvicorn
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

from .db import connect, init_db
from .html import esc, page
from .modpack import (
    UploadValidationError,
    build_storage_path,
    calculate_file_stats,
    generate_manifest,
    replace_build_files_from_zip,
    safe_manifest_path,
    safe_segment,
)
from .security import (
    create_build_access_token,
    create_session_token,
    hash_password,
    verify_build_access_token,
    verify_password,
    verify_session_token,
)
from .settings import APP_NAME, DEFAULT_HOST, DEFAULT_PORT, get_public_base_url, get_session_secret, get_storage_root


SESSION_COOKIE = "mslaunch_panel_session"
app = FastAPI(title=APP_NAME)


@app.on_event("startup")
def startup() -> None:
    init_db()


def get_current_user(request: Request) -> Row | None:
    token = request.cookies.get(SESSION_COOKIE, "")
    username = verify_session_token(token, get_session_secret())
    if not username:
        return None
    with connect() as connection:
        user = connection.execute(
            "SELECT * FROM users WHERE username=? AND active=1",
            (username,),
        ).fetchone()
    return user


def require_user(request: Request) -> Row:
    user = get_current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Login required.")
    return user


def require_owner(user: Annotated[Row, Depends(require_user)]) -> Row:
    if user["role"] != "owner":
        raise HTTPException(status_code=403, detail="Owner role required.")
    return user


def require_build_admin(user: Annotated[Row, Depends(require_user)]) -> Row:
    if user["role"] not in ("owner", "project_admin"):
        raise HTTPException(status_code=403, detail="Admin role required.")
    return user


def redirect_login() -> RedirectResponse:
    return RedirectResponse("/login", status_code=303)


def base_url_for(request: Request) -> str:
    return get_public_base_url(str(request.base_url).rstrip("/"))


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str = "") -> HTMLResponse:
    if get_current_user(request) is not None:
        return HTMLResponse("", status_code=303, headers={"location": "/"})
    message = f'<div class="error">{esc(error)}</div>' if error else ""
    body = f"""
    <div class="card" style="max-width:420px">
      {message}
      <form method="post" action="/login">
        <label>Login</label><input name="username" autocomplete="username">
        <label>Password</label><input name="password" type="password" autocomplete="current-password">
        <p><button>Enter panel</button></p>
      </form>
    </div>
    """
    return HTMLResponse(page(APP_NAME, body))


@app.post("/login")
def login(username: Annotated[str, Form()], password: Annotated[str, Form()]) -> RedirectResponse:
    with connect() as connection:
        user = connection.execute(
            "SELECT * FROM users WHERE username=? AND active=1",
            (username.strip(),),
        ).fetchone()
    if user is None or not verify_password(password, user["password_hash"]):
        return RedirectResponse("/login?error=Wrong+login+or+password", status_code=303)

    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(user["username"], get_session_secret()),
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 12,
    )
    return response


@app.post("/logout")
def logout() -> RedirectResponse:
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    user = get_current_user(request)
    if user is None:
        return redirect_login()

    with connect() as connection:
        projects = connection.execute("SELECT * FROM projects ORDER BY slug").fetchall()
        active_builds = connection.execute("SELECT * FROM builds WHERE status='active' ORDER BY project_slug").fetchall()
        open_reports = connection.execute("SELECT COUNT(*) AS count FROM reports WHERE status='open'").fetchone()["count"]

    project_cards = "".join(
        f'<div class="card"><b>{esc(row["name"])}</b><p class="muted">{esc(row["slug"])}</p></div>'
        for row in projects
    )
    build_rows = "".join(
        f"<tr><td>{esc(row['project_slug'])}</td><td>{esc(row['name'])}</td><td>{esc(row['minecraft_version'])}</td><td>{esc(row['file_count'])}</td></tr>"
        for row in active_builds
    ) or '<tr><td colspan="4" class="muted">No active builds yet.</td></tr>'
    body = f"""
    <div class="grid">
      <div class="card"><div class="muted">Signed in</div><b>{esc(user["username"])}</b><p>{esc(user["role"])}</p></div>
      <div class="card"><div class="muted">Open reports</div><b>{open_reports}</b></div>
    </div>
    <div class="grid">{project_cards}</div>
    <div class="card">
      <h2>Active builds</h2>
      <table><tr><th>Project</th><th>Build</th><th>Minecraft</th><th>Files</th></tr>{build_rows}</table>
    </div>
    """
    return HTMLResponse(page(APP_NAME, body, user=user))


@app.get("/builds", response_class=HTMLResponse)
def builds_page(request: Request):
    user = get_current_user(request)
    if user is None:
        return redirect_login()

    with connect() as connection:
        projects = connection.execute("SELECT * FROM projects ORDER BY slug").fetchall()
        builds = connection.execute("SELECT * FROM builds ORDER BY project_slug, created_at DESC").fetchall()

    project_options = "".join(f'<option value="{esc(row["slug"])}">{esc(row["name"])}</option>' for row in projects)
    build_rows = "".join(render_build_row(row) for row in builds) or '<tr><td colspan="8" class="muted">No builds yet.</td></tr>'
    body = f"""
    <div class="card">
      <h2>Create/update build</h2>
      <form method="post" action="/builds/create" enctype="multipart/form-data">
        <div class="row">
          <div><label>Project</label><select name="project_slug">{project_options}</select></div>
          <div><label>Build ID</label><input name="build_id" placeholder="nukem-1-20-1"></div>
          <div><label>Name</label><input name="name" placeholder="MS Nuckem 1.20.1"></div>
          <div><label>Minecraft</label><input name="minecraft_version" placeholder="1.20.1"></div>
          <div><label>Loader</label><select name="loader"><option>fabric</option><option>vanilla</option></select></div>
          <div><label>Loader version</label><input name="loader_version" value="latest"></div>
          <div><label>Server</label><input name="server"></div>
          <div><label>Port</label><input name="port"></div>
          <div><label>Build password</label><input name="access_password" type="password" placeholder="optional per-build code"></div>
        </div>
        <label>Modpack ZIP with mods/config/resourcepacks</label><input name="archive" type="file" accept=".zip">
        <p><label><input name="make_active" type="checkbox" value="1" style="width:auto"> Make active today</label></p>
        <button>Create build</button>
      </form>
    </div>
    <div class="card">
      <h2>Builds</h2>
      <table><tr><th>Project</th><th>ID</th><th>Name</th><th>MC</th><th>Loader</th><th>Files</th><th>Access</th><th>Status</th><th></th></tr>{build_rows}</table>
    </div>
    """
    return HTMLResponse(page("Builds", body, user=user))


def render_build_row(row: Row) -> str:
    activate = ""
    if row["status"] != "active":
        activate = f'<form method="post" action="/builds/{esc(row["project_slug"])}/{esc(row["build_id"])}/activate"><button>Activate</button></form>'
    return f"""
    <tr>
      <td>{esc(row["project_slug"])}</td>
      <td>{esc(row["build_id"])}</td>
      <td>{esc(row["name"])}</td>
      <td>{esc(row["minecraft_version"])}</td>
      <td>{esc(row["loader"])}</td>
      <td>{esc(row["file_count"])}</td>
      <td>{'locked' if row['access_hash_sha256'] else 'open'}</td>
      <td><span class="status {esc(row["status"])}">{esc(row["status"])}</span></td>
      <td>{activate}</td>
    </tr>
    """


@app.post("/builds/create")
def create_build(
    request: Request,
    user: Annotated[Row, Depends(require_build_admin)],
    project_slug: Annotated[str, Form()],
    build_id: Annotated[str, Form()],
    name: Annotated[str, Form()],
    minecraft_version: Annotated[str, Form()],
    loader: Annotated[str, Form()],
    loader_version: str = Form("latest"),
    server: str = Form(""),
    port: str = Form(""),
    access_password: str = Form(""),
    make_active: str = Form(""),
    archive: UploadFile | None = File(None),
) -> RedirectResponse:
    try:
        project = safe_segment(project_slug)
        build = safe_segment(build_id)
        if loader not in ("vanilla", "fabric"):
            raise UploadValidationError("Loader must be vanilla or fabric.")
        if port and (not port.isdigit() or not 1 <= int(port) <= 65535):
            raise UploadValidationError("Port must be 1..65535.")

        files_root = build_storage_path(get_storage_root(), project, build)
        if archive is not None and archive.filename:
            if not archive.filename.lower().endswith(".zip"):
                raise UploadValidationError("MVP accepts .zip only. Repack .rar as zip first.")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
                shutil.copyfileobj(archive.file, tmp)
                tmp_path = Path(tmp.name)
            try:
                replace_build_files_from_zip(tmp_path, files_root)
            finally:
                tmp_path.unlink(missing_ok=True)
        else:
            files_root.mkdir(parents=True, exist_ok=True)

        file_count, total_size = calculate_file_stats(files_root)
        status = "active" if make_active else "draft"
        access_hash = hash_build_access_password(access_password)
        with connect() as connection:
            if status == "active":
                connection.execute("UPDATE builds SET status='archived' WHERE project_slug=? AND status='active'", (project,))
            connection.execute(
                """
                INSERT INTO builds (
                    project_slug, build_id, name, minecraft_version, loader, loader_version,
                    server, port, access_hash_sha256, status, file_count, total_size, created_by, activated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CASE WHEN ?='active' THEN CURRENT_TIMESTAMP ELSE '' END)
                ON CONFLICT(project_slug, build_id) DO UPDATE SET
                    name=excluded.name,
                    minecraft_version=excluded.minecraft_version,
                    loader=excluded.loader,
                    loader_version=excluded.loader_version,
                    server=excluded.server,
                    port=excluded.port,
                    access_hash_sha256=CASE
                        WHEN excluded.access_hash_sha256 != '' THEN excluded.access_hash_sha256
                        ELSE builds.access_hash_sha256
                    END,
                    status=excluded.status,
                    file_count=excluded.file_count,
                    total_size=excluded.total_size,
                    created_by=excluded.created_by,
                    activated_at=excluded.activated_at
                """,
                (
                    project,
                    build,
                    name.strip() or build,
                    minecraft_version.strip(),
                    loader,
                    loader_version.strip() or "latest",
                    server.strip(),
                    port.strip(),
                    access_hash,
                    status,
                    file_count,
                    total_size,
                    user["username"],
                    status,
                ),
            )
    except UploadValidationError as exc:
        return RedirectResponse(f"/builds?error={esc(exc)}", status_code=303)

    return RedirectResponse("/builds", status_code=303)


@app.post("/builds/{project}/{build_id}/activate")
def activate_build(project: str, build_id: str, user: Annotated[Row, Depends(require_build_admin)]) -> RedirectResponse:
    with connect() as connection:
        connection.execute("UPDATE builds SET status='archived' WHERE project_slug=? AND status='active'", (project,))
        connection.execute(
            "UPDATE builds SET status='active', activated_at=CURRENT_TIMESTAMP WHERE project_slug=? AND build_id=?",
            (project, build_id),
        )
    return RedirectResponse("/builds", status_code=303)


def hash_build_access_password(password: str) -> str:
    password = password.strip()
    if not password:
        return ""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def get_build_access_hash(project: str, build_id: str) -> str:
    with connect() as connection:
        row = connection.execute(
            "SELECT access_hash_sha256 FROM builds WHERE project_slug=? AND build_id=?",
            (project, build_id),
        ).fetchone()
    return str(row["access_hash_sha256"] or "") if row is not None else ""


def assert_build_file_access(project: str, build_id: str, access: str) -> None:
    access_hash = get_build_access_hash(project, build_id)
    if not access_hash:
        return
    if verify_build_access_token(access, project, build_id, get_session_secret()):
        return
    raise HTTPException(status_code=403, detail="Build access password required.")


@app.get("/updates", response_class=HTMLResponse)
def updates_page(request: Request):
    user = get_current_user(request)
    if user is None:
        return redirect_login()
    with connect() as connection:
        rows = connection.execute("SELECT * FROM launcher_updates ORDER BY created_at DESC").fetchall()
    rendered = "".join(
        f"<tr><td>{esc(row['version'])}</td><td>{esc(row['enabled'])}</td><td>{esc(row['download_url'])}</td><td>{esc(row['notes'])}</td></tr>"
        for row in rows
    ) or '<tr><td colspan="4" class="muted">No update notices.</td></tr>'
    body = f"""
    <div class="card">
      <h2>Launcher update notice</h2>
      <form method="post" action="/updates/create">
        <div class="row">
          <div><label>Version</label><input name="version" placeholder="1.9.1"></div>
          <div><label>Download URL</label><input name="download_url"></div>
          <div><label>SHA256</label><input name="sha256"></div>
        </div>
        <label>Notes</label><textarea name="notes"></textarea>
        <p><label><input name="enabled" type="checkbox" value="1" style="width:auto"> Enabled</label></p>
        <button>Save update</button>
      </form>
    </div>
    <div class="card"><table><tr><th>Version</th><th>Enabled</th><th>URL</th><th>Notes</th></tr>{rendered}</table></div>
    """
    return HTMLResponse(page("Updates", body, user=user))


@app.post("/updates/create")
def create_update(
    user: Annotated[Row, Depends(require_owner)],
    version: Annotated[str, Form()],
    download_url: str = Form(""),
    sha256: str = Form(""),
    notes: str = Form(""),
    enabled: str = Form(""),
) -> RedirectResponse:
    with connect() as connection:
        if enabled:
            connection.execute("UPDATE launcher_updates SET enabled=0")
        connection.execute(
            "INSERT INTO launcher_updates (version, download_url, sha256, notes, enabled) VALUES (?, ?, ?, ?, ?)",
            (version.strip(), download_url.strip(), sha256.strip().lower(), notes.strip(), 1 if enabled else 0),
        )
    return RedirectResponse("/updates", status_code=303)


@app.get("/reports", response_class=HTMLResponse)
def reports_page(request: Request):
    user = get_current_user(request)
    if user is None:
        return redirect_login()
    with connect() as connection:
        rows = connection.execute("SELECT * FROM reports ORDER BY created_at DESC LIMIT 200").fetchall()
    rendered = "".join(
        f"<tr><td>{esc(row['created_at'])}</td><td>{esc(row['project'])}</td><td>{esc(row['username'])}</td><td>{esc(row['error_type'])}</td><td>{esc(row['status'])}</td><td><a href='/reports/{row['id']}'>Open</a></td></tr>"
        for row in rows
    ) or '<tr><td colspan="6" class="muted">No reports yet.</td></tr>'
    body = f'<div class="card"><table><tr><th>Time</th><th>Project</th><th>User</th><th>Type</th><th>Status</th><th></th></tr>{rendered}</table></div>'
    return HTMLResponse(page("Reports", body, user=user))


@app.get("/reports/{report_id}", response_class=HTMLResponse)
def report_detail(report_id: int, request: Request):
    user = get_current_user(request)
    if user is None:
        return redirect_login()
    with connect() as connection:
        row = connection.execute("SELECT * FROM reports WHERE id=?", (report_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    body = f"""
    <div class="card">
      <p><b>{esc(row['error_type'])}</b> <span class="muted">{esc(row['created_at'])}</span></p>
      <p>{esc(row['project'])} / {esc(row['build_id'])} / {esc(row['username'])}</p>
      <h3>User message</h3><pre>{esc(row['user_message'])}</pre>
      <h3>Technical details</h3><pre>{esc(row['technical_details'])}</pre>
      <form method="post" action="/reports/{report_id}/resolve"><button>Mark resolved</button></form>
    </div>
    """
    return HTMLResponse(page("Report", body, user=user))


@app.post("/reports/{report_id}/resolve")
def resolve_report(report_id: int, user: Annotated[Row, Depends(require_build_admin)]) -> RedirectResponse:
    with connect() as connection:
        connection.execute("UPDATE reports SET status='resolved' WHERE id=?", (report_id,))
    return RedirectResponse("/reports", status_code=303)


@app.get("/admins", response_class=HTMLResponse)
def admins_page(request: Request):
    user = get_current_user(request)
    if user is None:
        return redirect_login()
    if user["role"] != "owner":
        return HTMLResponse(page("Admins", '<div class="error">Owner role required.</div>', user=user), status_code=403)
    with connect() as connection:
        users = connection.execute("SELECT * FROM users ORDER BY username").fetchall()
    rows = "".join(
        f"<tr><td>{esc(row['username'])}</td><td>{esc(row['role'])}</td><td>{esc(row['active'])}</td><td><form method='post' action='/admins/{esc(row['username'])}/deactivate'><button class='danger'>Deactivate</button></form></td></tr>"
        for row in users
    )
    body = f"""
    <div class="card">
      <form method="post" action="/admins/create">
        <div class="row">
          <div><label>Username</label><input name="username"></div>
          <div><label>Password</label><input name="password" type="password"></div>
          <div><label>Role</label><select name="role"><option>project_admin</option><option>owner</option><option>viewer</option></select></div>
        </div>
        <button>Create/reset admin</button>
      </form>
    </div>
    <div class="card"><table><tr><th>User</th><th>Role</th><th>Active</th><th></th></tr>{rows}</table></div>
    """
    return HTMLResponse(page("Admins", body, user=user))


@app.post("/admins/create")
def create_admin(
    user: Annotated[Row, Depends(require_owner)],
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    role: str = Form("project_admin"),
) -> RedirectResponse:
    if role not in ("owner", "project_admin", "viewer"):
        raise HTTPException(status_code=400, detail="Invalid role.")
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO users (username, password_hash, role, active)
            VALUES (?, ?, ?, 1)
            ON CONFLICT(username) DO UPDATE SET password_hash=excluded.password_hash, role=excluded.role, active=1
            """,
            (username.strip(), hash_password(password), role),
        )
    return RedirectResponse("/admins", status_code=303)


@app.post("/admins/{username}/deactivate")
def deactivate_admin(username: str, user: Annotated[Row, Depends(require_owner)]) -> RedirectResponse:
    with connect() as connection:
        connection.execute("UPDATE users SET active=0 WHERE username=?", (username,))
    return RedirectResponse("/admins", status_code=303)


@app.get("/api/projects/{project}/active-build")
def api_active_build(project: str, request: Request) -> JSONResponse:
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM builds WHERE project_slug=? AND status='active' ORDER BY activated_at DESC, created_at DESC LIMIT 1",
            (project,),
        ).fetchone()
        update = connection.execute(
            "SELECT * FROM launcher_updates WHERE enabled=1 ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="No active build.")
    manifest_url = str(request.url_for("api_manifest", project=project, build_id=row["build_id"]))
    data = build_api_payload(row, manifest_url)
    if update is not None:
        data.update(
            {
                "launcher_version": update["version"],
                "launcher_download_url": update["download_url"],
                "launcher_sha256": update["sha256"],
                "launcher_notes": update["notes"],
            }
        )
    return JSONResponse(data)


def build_api_payload(row: Row, manifest_url: str) -> dict[str, str]:
    return {
        "project": row["project_slug"],
        "build_id": row["build_id"],
        "id": row["build_id"],
        "name": row["name"],
        "minecraft_version": row["minecraft_version"],
        "loader": row["loader"],
        "loader_version": row["loader_version"],
        "manifest_url": manifest_url,
        "server": row["server"],
        "port": row["port"],
        "access_required": "true" if row["access_hash_sha256"] else "",
        "source": "panel",
        "launcher_version": "",
        "launcher_download_url": "",
        "launcher_sha256": "",
        "launcher_notes": "",
    }


@app.post("/api/projects/{project}/builds/{build_id}/access")
async def api_build_access(project: str, build_id: str, request: Request) -> JSONResponse:
    payload = await request.json()
    password = clean_text(payload.get("password"), 400)
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM builds WHERE project_slug=? AND build_id=?",
            (project, build_id),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Build not found.")

    access_hash = str(row["access_hash_sha256"] or "")
    if access_hash:
        actual_hash = hash_build_access_password(password)
        if not hmac.compare_digest(actual_hash, access_hash):
            raise HTTPException(status_code=403, detail="Wrong build password.")

    token = create_build_access_token(project, build_id, get_session_secret())
    manifest_url = str(request.url_for("api_manifest", project=project, build_id=build_id)) + f"?access={token}"
    return JSONResponse({"manifest_url": manifest_url, "access_token": token})


@app.get("/api/projects/{project}/builds/{build_id}/manifest.json", name="api_manifest")
def api_manifest(project: str, build_id: str, request: Request, access: str = "") -> JSONResponse:
    assert_build_file_access(project, build_id, access)
    files_root = build_storage_path(get_storage_root(), project, build_id)
    files_base_url = str(request.url_for("file_download", project=project, build_id=build_id, file_path="")).rstrip("/")
    manifest = generate_manifest(files_root, files_base_url)
    if access:
        for item in manifest.get("files", []):
            if isinstance(item, dict) and item.get("url"):
                item["url"] = f"{item['url']}?access={access}"
    return JSONResponse(manifest)


@app.get("/files/{project}/{build_id}/{file_path:path}", name="file_download")
def file_download(project: str, build_id: str, file_path: str, access: str = "") -> FileResponse:
    assert_build_file_access(project, build_id, access)
    relative_path = safe_manifest_path(file_path)
    target = build_storage_path(get_storage_root(), project, build_id) / Path(relative_path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(target)


@app.get("/api/launcher/update")
def api_launcher_update() -> JSONResponse:
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM launcher_updates WHERE enabled=1 ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    if row is None:
        return JSONResponse({"enabled": False})
    return JSONResponse(
        {
            "enabled": True,
            "version": row["version"],
            "download_url": row["download_url"],
            "sha256": row["sha256"],
            "notes": row["notes"],
        }
    )


@app.post("/api/reports")
async def api_reports(request: Request) -> JSONResponse:
    payload = await request.json()
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO reports (
                project, build_id, username, launcher_version, error_type, user_message, technical_details
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                clean_text(payload.get("project"), 80),
                clean_text(payload.get("build_id"), 120),
                clean_text(payload.get("username"), 120),
                clean_text(payload.get("launcher_version"), 40),
                clean_text(payload.get("error_type"), 80),
                clean_text(payload.get("user_message"), 4000),
                clean_text(payload.get("technical_details"), 20000),
            ),
        )
    return JSONResponse({"ok": True})


def clean_text(value: object, limit: int) -> str:
    return str(value or "").strip()[:limit]


def main() -> None:
    uvicorn.run("admin_panel.app:app", host=DEFAULT_HOST, port=DEFAULT_PORT, reload=False)


if __name__ == "__main__":
    main()
