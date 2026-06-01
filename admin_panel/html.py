from __future__ import annotations

from html import escape
from sqlite3 import Row


CSS = """
body { margin:0; background:#0d1117; color:#e6edf3; font-family:Segoe UI,Arial,sans-serif; }
a { color:#7ee3b6; text-decoration:none; }
.shell { max-width:1180px; margin:0 auto; padding:28px; }
.top { display:flex; align-items:center; justify-content:space-between; margin-bottom:24px; }
.brand { font-size:24px; font-weight:800; }
.nav a, .nav button { margin-left:8px; }
.card { background:#151b23; border:1px solid #30363d; border-radius:8px; padding:18px; margin-bottom:16px; }
.grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:16px; }
.muted { color:#9198a1; }
.status { display:inline-flex; padding:3px 8px; border:1px solid #3fb950; border-radius:999px; color:#7ee787; font-size:12px; }
.status.draft { border-color:#d29922; color:#f2cc60; }
.status.archived { border-color:#8b949e; color:#c9d1d9; }
table { width:100%; border-collapse:collapse; }
th,td { padding:10px; border-bottom:1px solid #30363d; text-align:left; vertical-align:top; }
input,select,textarea { width:100%; box-sizing:border-box; background:#0d1117; color:#e6edf3; border:1px solid #30363d; border-radius:6px; padding:9px; }
label { display:block; font-size:13px; color:#c9d1d9; margin:8px 0 5px; }
button,.button { display:inline-block; background:#238636; color:#fff; border:0; border-radius:6px; padding:9px 13px; font-weight:700; cursor:pointer; }
button.secondary,.button.secondary { background:#21262d; border:1px solid #30363d; }
button.danger { background:#da3633; }
.button.primary { background:linear-gradient(135deg,#ff9d1a,#ff6b00); color:#111; padding:13px 18px; border-radius:10px; box-shadow:0 10px 30px rgba(255,132,0,.25); }
.hero { min-height:72vh; display:grid; align-items:center; background:radial-gradient(circle at 20% 20%, rgba(126,227,182,.16), transparent 38%), #10161d; border:1px solid #30363d; border-radius:16px; padding:42px; }
.hero h1 { font-size:48px; margin:8px 0 12px; }
.hero p { max-width:620px; color:#c9d1d9; font-size:18px; line-height:1.45; }
.eyebrow { color:#7ee3b6; text-transform:uppercase; letter-spacing:.08em; font-size:12px; font-weight:800; }
.row { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; }
.error { background:#3d1518; border:1px solid #da3633; color:#ffdcd7; padding:12px; border-radius:6px; }
.ok { background:#12331f; border:1px solid #238636; color:#d8ffe2; padding:12px; border-radius:6px; }
pre { white-space:pre-wrap; background:#0d1117; border:1px solid #30363d; border-radius:6px; padding:12px; }
"""


def page(title: str, body: str, *, user: Row | None = None) -> str:
    nav = ""
    if user is not None:
        nav = """
        <div class="nav">
          <a class="button secondary" href="/">Dashboard</a>
          <a class="button secondary" href="/builds">Builds</a>
          <a class="button secondary" href="/updates">Updates</a>
          <a class="button secondary" href="/reports">Reports</a>
          <a class="button secondary" href="/admins">Admins</a>
          <form action="/logout" method="post" style="display:inline"><button class="secondary">Logout</button></form>
        </div>
        """
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>{CSS}</style>
</head>
<body>
  <main class="shell">
    <div class="top"><div class="brand">{escape(title)}</div>{nav}</div>
    {body}
  </main>
</body>
</html>"""


def esc(value: object) -> str:
    return escape(str(value or ""))
