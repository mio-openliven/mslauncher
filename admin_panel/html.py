from __future__ import annotations

from html import escape
from sqlite3 import Row


CSS = """
body { margin:0; background:#0d1117; color:#e6edf3; font-family:Segoe UI,Arial,sans-serif; }
a { color:#7ee3b6; text-decoration:none; }
.shell { max-width:1180px; margin:0 auto; padding:28px; }
.top { display:flex; align-items:center; justify-content:space-between; margin-bottom:24px; }
.brandWrap { display:flex; align-items:center; gap:12px; min-width:260px; }
.brandLogo { width:46px; height:46px; object-fit:contain; filter:drop-shadow(0 0 14px rgba(126,227,182,.25)); }
.brand { font-size:24px; font-weight:850; letter-spacing:.01em; }
.brandSub { color:#7ee3b6; font-size:12px; font-weight:800; margin-top:2px; }
.nav { display:flex; align-items:center; gap:8px; flex-wrap:wrap; justify-content:flex-end; }
.nav a, .nav button { margin-left:0; }
.langSwitch { display:inline-flex; align-items:center; gap:4px; padding:4px; border:1px solid #30363d; border-radius:12px; background:#151b23; margin-right:8px; }
.langButton { min-width:54px; text-align:center; padding:9px 10px; border-radius:9px; color:#c9d1d9; font-weight:900; letter-spacing:.04em; }
.langButton.active { background:#7ee3b6; color:#08110d; box-shadow:0 0 0 1px rgba(126,227,182,.35), 0 10px 26px rgba(126,227,182,.18); }
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
.notice { max-width:680px; margin-top:18px; padding:14px 16px; border:1px solid #d29922; border-radius:10px; background:rgba(210,153,34,.12); color:#ffe8ad; line-height:1.5; }
.notice code { display:block; margin-top:8px; word-break:break-all; color:#e6edf3; font-size:12px; }
.row { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:12px; }
.error { background:#3d1518; border:1px solid #da3633; color:#ffdcd7; padding:12px; border-radius:6px; }
.ok { background:#12331f; border:1px solid #238636; color:#d8ffe2; padding:12px; border-radius:6px; }
pre { white-space:pre-wrap; background:#0d1117; border:1px solid #30363d; border-radius:6px; padding:12px; }
"""


LABELS = {
    "ru": {
        "dashboard": "Главная",
        "builds": "Сборки",
        "updates": "Обновления",
        "reports": "Отчёты",
        "admins": "Админы",
        "logout": "Выйти",
        "project_panel": "кабинет проекта",
    },
    "en": {
        "dashboard": "Dashboard",
        "builds": "Builds",
        "updates": "Updates",
        "reports": "Reports",
        "admins": "Admins",
        "logout": "Logout",
        "project_panel": "project panel",
    },
}


def page(
    title: str,
    body: str,
    *,
    user: Row | None = None,
    lang: str = "ru",
    project_name: str = "",
    project_slug: str = "",
) -> str:
    lang = "en" if lang == "en" else "ru"
    labels = LABELS[lang]
    project_slug = project_slug or str(user["project_slug"] if user is not None and "project_slug" in user.keys() else "")
    brand_name = project_name or title
    logo = ""
    if project_slug == "nukem":
        logo = '<img class="brandLogo" src="/downloads/nukem.png" alt="">'
        brand_name = "MS Nuckem"
    elif project_slug:
        brand_name = project_name or project_slug
    language_switch = f"""
      <div class="langSwitch" aria-label="Language">
        <a class="langButton {'active' if lang == 'ru' else ''}" href="/language/ru">RU</a>
        <a class="langButton {'active' if lang == 'en' else ''}" href="/language/en">ENG</a>
      </div>
    """
    nav = language_switch
    if user is not None:
        admins_link = '<a class="button secondary" href="/admins">{}</a>'.format(labels["admins"]) if user["role"] == "owner" else ""
        nav = f"""
        <div class="nav">
          {language_switch}
          <a class="button secondary" href="/">{labels["dashboard"]}</a>
          <a class="button secondary" href="/builds">{labels["builds"]}</a>
          <a class="button secondary" href="/updates">{labels["updates"]}</a>
          <a class="button secondary" href="/reports">{labels["reports"]}</a>
          {admins_link}
          <form action="/logout" method="post" style="display:inline"><button class="secondary">{labels["logout"]}</button></form>
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
    <div class="top">
      <div class="brandWrap">
        {logo}
        <div><div class="brand">{escape(brand_name)}</div><div class="brandSub">{escape(labels["project_panel"])}</div></div>
      </div>
      {nav}
    </div>
    {body}
  </main>
</body>
</html>"""


def esc(value: object) -> str:
    return escape(str(value or ""))
