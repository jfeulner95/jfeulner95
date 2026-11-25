#!/usr/bin/env python3
"""Generates the bento-grid profile card and project cards, in dark and light.

    assets/bento-dark.svg / bento-light.svg
    assets/project-<repo>-dark.svg / -light.svg

Static content lives in PROFILE below. Live data (contributions, repos,
followers, project language and last update) is fetched from GitHub on every
run. Only the standard library is used, so this runs anywhere with Python 3.8+.

    python3 scripts/generate_bento.py

Set GITHUB_TOKEN to avoid API rate limits (the GitHub Action does this).
"""

import datetime as dt
import json
import os
import re
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

# ── Edit me ──────────────────────────────────────────────────────────────────
PROFILE = {
    "username": "jfeulner95",
    "greeting": "HELLO, I'M",
    "name": "Johannes Feulner",
    "role": "Embedded Dev & AI Tinkerer",
    "bio": [
        "Embedded developer by day, AI-workflow tinkerer by night.",
        "I like making hardware and tools talk to each other.",
    ],
    "status": "currently tinkering",
    # (label, accent colour)
    "languages": [("C", "#5c9eff"), ("C++", "#f34b7d"), ("Python", "#ffd43b"), ("Swift", "#f05138"),
                  ("Bash", "#4ade80"), ("Matlab", "#3b9be0"), ("Simulink", "#22d3ee")],
    "tools": [("Linux", "#fbbf24"), ("macOS", "#e5e7eb"), ("Windows", "#38bdf8"), ("Docker", "#2496ed"),
              ("GitHub", "#9ca3af"), ("GitLab", "#fc6d26"), ("OpenAI", "#10a37f"), ("Claude Code", "#d97757")],
    # Project cards: repo name, tagline, topics line, glow colour.
    # After adding/removing a project, add/remove its card in README.md too.
    "projects": [
        ("claude-cheat-sheet", "Claude Code on one page.",
         "cli · slash commands · shortcuts · mcp · hooks", "#d97757"),
        ("git-cheat-sheet", "Git, from first clone to rebase.",
         "branches · merge & rebase · undo · stash · tags", "#f472b6"),
        ("ClaudeCodeSkillSummary", "The best Claude Code skills, in one place.",
         "skills · plugins · one-line install · updates", "#a78bfa"),
        ("jfeulner95", "This profile – generated, not drawn.",
         "python · svg · github actions · nightly stats", "#38bdf8"),
    ],
}
# ─────────────────────────────────────────────────────────────────────────────

ASSETS = Path(__file__).resolve().parent.parent / "assets"
W, H, GAP = 840, 432, 12
PW, PH = (W - GAP) // 2, 172  # project card size: two cards span the bento width

THEMES = {
    "dark": dict(tile="#0f1117", line="#ffffff", line_op=0.08, text="#e6e8ee", muted="#8a8f9c",
                 bio="#a3a8b4", chip="#ffffff", chip_op=0.05, glow_op=0.22, ok="#4ade80",
                 brand=("#38bdf8", "#a78bfa", "#f472b6")),
    "light": dict(tile="#f6f8fa", line="#1f2328", line_op=0.10, text="#1f2328", muted="#656d76",
                  bio="#424a53", chip="#ffffff", chip_op=1.0, glow_op=0.16, ok="#16a34a",
                  brand=("#0284c7", "#7c3aed", "#db2777")),
}

LANG_COLORS = {"C": "#5c9eff", "C++": "#f34b7d", "Python": "#ffd43b", "Shell": "#4ade80",
               "Swift": "#f05138", "JavaScript": "#f1e05a", "TypeScript": "#3178c6"}


# ── Data ─────────────────────────────────────────────────────────────────────

def fetch(url, accept="application/vnd.github+json"):
    headers = {"Accept": accept, "User-Agent": "profile-bento-generator"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as r:
        return r.read().decode("utf-8")


def get_stats(user):
    stats = {"contributions": None, "repos": None, "followers": None, "years": None}
    try:
        u = json.loads(fetch(f"https://api.github.com/users/{user}"))
        stats["repos"], stats["followers"] = u["public_repos"], u["followers"]
        stats["years"] = dt.date.today().year - int(u["created_at"][:4])
    except Exception as e:  # keep going with partial data
        print(f"warning: GitHub API: {e}")
    try:
        html = fetch(f"https://github.com/users/{user}/contributions", accept="text/html")
        m = re.search(r"([\d,]+)\s+contributions?\s+in the last year", html)
        if m:
            stats["contributions"] = int(m.group(1).replace(",", ""))
    except Exception as e:
        print(f"warning: contributions: {e}")
    return stats


def get_repo(user, name):
    try:
        r = json.loads(fetch(f"https://api.github.com/repos/{user}/{name}"))
        return {"language": r.get("language"), "pushed": r["pushed_at"][:10], "stars": r["stargazers_count"]}
    except Exception as e:
        print(f"warning: repo {name}: {e}")
        return {"language": None, "pushed": None, "stars": None}


# ── Helpers ──────────────────────────────────────────────────────────────────

def fmt(n):
    if n is None:
        return "–"
    return f"{n / 1000:.1f}k".replace(".0k", "k") if n >= 1000 else str(n)


def ago(iso):
    if not iso:
        return ""
    days = (dt.date.today() - dt.date.fromisoformat(iso)).days
    if days <= 0:
        return "updated today"
    if days == 1:
        return "updated yesterday"
    if days < 30:
        return f"updated {days} days ago"
    return "updated " + dt.date.fromisoformat(iso).strftime("%b %Y")


def dot(color, t):
    """Very light dots vanish on light tiles – swap them for a neutral grey."""
    r, g, b = (int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    lin = lambda c: c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    lum = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
    return "#6e7781" if t is THEMES["light"] and lum > 0.75 else color


def tile(t, x, y, w, h, glow, delay, body):
    gid = f"g{x}_{y}"
    return f"""
  <g class="tile" style="animation-delay:{delay}s">
    <radialGradient id="{gid}" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse"
        gradientTransform="translate({x} {y}) scale({w * 0.9} {h * 1.1})">
      <stop offset="0" stop-color="{glow}" stop-opacity="{t['glow_op']}"/>
      <stop offset="1" stop-color="{glow}" stop-opacity="0"/>
    </radialGradient>
    <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="20" fill="{t['tile']}"/>
    <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="20" fill="url(#{gid})"/>
    <rect x="{x + .5}" y="{y + .5}" width="{w - 1}" height="{h - 1}" rx="19.5" fill="none"
          stroke="{t['line']}" stroke-opacity="{t['line_op']}"/>
    {body}
  </g>"""


def chips(t, items, x0, y0, max_w, mono=False):
    out, x, y = [], x0, y0
    char_w = 8.2 if mono else 7.6
    for label, color in items:
        w = len(label) * char_w + 38
        if x + w > x0 + max_w:
            x, y = x0, y + 42
        out.append(
            f'<rect x="{x}" y="{y}" width="{w:.0f}" height="32" rx="16" fill="{t["chip"]}" '
            f'fill-opacity="{t["chip_op"]}" stroke="{t["line"]}" stroke-opacity="{t["line_op"]}"/>'
            f'<circle cx="{x + 16}" cy="{y + 16}" r="4.5" fill="{dot(color, t)}"/>'
            f'<text x="{x + 28}" y="{y + 21}" class="chip{" mono" if mono else ""}">{escape(label)}</text>')
        x += w + 8
    return "".join(out)


def svg(t, w, h, label, body, extra_css=""):
    b = t["brand"]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img"
     aria-label="{escape(label)}">
  <defs>
    <linearGradient id="brand" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="{b[0]}"/><stop offset="0.5" stop-color="{b[1]}"/><stop offset="1" stop-color="{b[2]}"/>
    </linearGradient>
  </defs>
  <style>
    text {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, Helvetica, Arial, sans-serif; fill: {t['text']}; }}
    .mono {{ font-family: 'SF Mono', 'JetBrains Mono', Menlo, Consolas, monospace; }}
    .eyebrow {{ font-size: 11px; font-weight: 600; letter-spacing: 2px; fill: {t['muted']}; }}
    .label {{ font-size: 12px; fill: {t['muted']}; }}
    .chip {{ font-size: 13px; font-weight: 600; }}
    .tile {{ animation: rise .7s cubic-bezier(.2,.8,.2,1) backwards; }}
    @keyframes rise {{ from {{ opacity: 0; transform: translateY(14px); }} to {{ opacity: 1; transform: none; }} }}
    {extra_css}
  </style>
{body}
</svg>
"""


# ── Bento card ───────────────────────────────────────────────────────────────

def build_bento(p, s, t):
    today = dt.date.today().isoformat()
    col1, row2 = 528, 220 + GAP
    hero = f"""
    <text x="28" y="44" class="eyebrow">{escape(p['greeting'])}</text>
    <text x="28" y="94" class="name">{escape(p['name'])}</text>
    <text x="28" y="128" class="role">{escape(p['role'])}</text>
    <text x="28" y="164" class="bio">{escape(p['bio'][0])}</text>
    <text x="28" y="186" class="bio">{escape(p['bio'][1])}</text>
    <circle cx="{col1 - 150}" cy="40" r="4" fill="{t['ok']}" class="pulse"/>
    <circle cx="{col1 - 150}" cy="40" r="4" fill="{t['ok']}"/>
    <text x="{col1 - 138}" y="44" class="label">{escape(p['status'])}</text>"""

    sx, sw = col1 + GAP, W - col1 - GAP
    cells = [("contributions", "contributions · 1y"), ("repos", "public repos"),
             ("years", "years on GitHub"), ("followers", "followers")]
    stat_body = [f'<text x="{sx + 24}" y="44" class="eyebrow">GITHUB · LIVE</text>',
                 f'<text x="{sx + sw - 20}" y="44" class="label" text-anchor="end">{today}</text>']
    for i, (key, label) in enumerate(cells):
        cx = sx + 24 + (i % 2) * (sw / 2 - 8)
        cy = 104 + (i // 2) * 74
        stat_body.append(f'<text x="{cx}" y="{cy}" class="num">{fmt(s[key])}</text>'
                         f'<text x="{cx}" y="{cy + 20}" class="label">{label}</text>')

    lw = 330
    langs = (f'<text x="24" y="{row2 + 38}" class="eyebrow">LANGUAGES</text>'
             + chips(t, p["languages"], 24, row2 + 60, lw - 40, mono=True))

    tx, tw = lw + GAP, 330
    tools = (f'<text x="{tx + 24}" y="{row2 + 38}" class="eyebrow">PLATFORMS &amp; TOOLS</text>'
             + chips(t, p["tools"], tx + 24, row2 + 60, tw - 40))

    ex = tx + tw + GAP
    ew, hh = W - ex, H - row2
    wave_y, period = row2 + 72, 36
    wave = f"M{ex - period * 2},{wave_y + 18}"
    for i in range(12):
        x = ex - period * 2 + i * period
        wave += f" V{wave_y - 18} H{x + period / 2} V{wave_y + 18} H{x + period}"
    signal = f"""
    <clipPath id="wclip"><rect x="{ex}" y="{row2}" width="{ew}" height="{hh}" rx="20"/></clipPath>
    <text x="{ex + 24}" y="{row2 + 38}" class="eyebrow">SIGNAL</text>
    <g clip-path="url(#wclip)"><path d="{wave}" class="wave" stroke="url(#brand)"/></g>
    <text x="{ex + 24}" y="{row2 + hh - 46}" class="big">bits → bots</text>
    <text x="{ex + 24}" y="{row2 + hh - 24}" class="label">embedded meets AI</text>"""

    css = f"""
    .name {{ font-size: 42px; font-weight: 800; letter-spacing: -1.2px; }}
    .role {{ font-size: 21px; font-weight: 700; fill: url(#brand); }}
    .bio {{ font-size: 14.5px; fill: {t['bio']}; }}
    .num {{ font-size: 36px; font-weight: 800; letter-spacing: -1px; }}
    .big {{ font-size: 20px; font-weight: 800; letter-spacing: -0.4px; }}
    .wave {{ fill: none; stroke-width: 2.5; stroke-linejoin: round; animation: scroll 1.6s linear infinite; }}
    .pulse {{ transform-box: fill-box; transform-origin: center; animation: pulse 2s ease-out infinite; }}
    @keyframes pulse {{ from {{ transform: scale(1); opacity: .7; }} to {{ transform: scale(3.5); opacity: 0; }} }}
    @keyframes scroll {{ from {{ transform: translateX(0); }} to {{ transform: translateX({period}px); }} }}"""

    body = "".join([
        tile(t, 0, 0, col1, 220, t["brand"][1], 0.0, hero),
        tile(t, sx, 0, sw, 220, t["brand"][0], 0.12, "".join(stat_body)),
        tile(t, 0, row2, lw, hh, "#5c9eff", 0.24, langs),
        tile(t, tx, row2, tw, hh, t["brand"][2], 0.36, tools),
        tile(t, ex, row2, ew, hh, t["ok"], 0.48, signal),
    ])
    return svg(t, W, H, f"{p['name']} – {p['role']}", body, css)


# ── Project card ─────────────────────────────────────────────────────────────

def build_project(name, tagline, topics, glow, info, t, delay):
    lang = info["language"]
    footer = []
    x = 24
    if lang:
        footer.append(f'<circle cx="{x + 5}" cy="{PH - 30}" r="5" fill="{dot(LANG_COLORS.get(lang, "#9ca3af"), t)}"/>'
                      f'<text x="{x + 16}" y="{PH - 26}" class="label">{escape(lang)}</text>')
        x += 16 + len(lang) * 7 + 18
    if info["stars"]:
        footer.append(f'<text x="{x}" y="{PH - 26}" class="label">★ {info["stars"]}</text>')
    footer.append(f'<text x="{PW - 24}" y="{PH - 26}" class="label" text-anchor="end">{ago(info["pushed"])}</text>')

    body = f"""
    <text x="24" y="38" class="eyebrow">PROJECT</text>
    <text x="{PW - 24}" y="42" class="arrow" text-anchor="end">↗</text>
    <text x="24" y="74" class="repo">{escape(name)}</text>
    <text x="24" y="100" class="tag">{escape(tagline)}</text>
    <text x="24" y="122" class="topics mono">{escape(topics)}</text>
    {''.join(footer)}"""
    css = f"""
    .repo {{ font-size: 22px; font-weight: 800; letter-spacing: -0.5px; }}
    .tag {{ font-size: 14.5px; fill: {t['bio']}; }}
    .topics {{ font-size: 11.5px; fill: {t['muted']}; }}
    .arrow {{ font-size: 18px; fill: url(#brand); font-weight: 700; }}"""
    return svg(t, PW, PH, f"{name} – {tagline}", tile(t, 0, 0, PW, PH, glow, delay, body), css)


# ── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    p = PROFILE
    stats = get_stats(p["username"])
    print("stats:", stats)
    ASSETS.mkdir(parents=True, exist_ok=True)
    for mode, t in THEMES.items():
        (ASSETS / f"bento-{mode}.svg").write_text(build_bento(p, stats, t), encoding="utf-8")
    for i, (name, tagline, topics, glow) in enumerate(p["projects"]):
        info = get_repo(p["username"], name)
        print(f"{name}:", info)
        for mode, t in THEMES.items():
            (ASSETS / f"project-{name}-{mode}.svg").write_text(
                build_project(name, tagline, topics, glow, info, t, 0.6 + i * 0.12), encoding="utf-8")
    print(f"wrote {ASSETS}")
