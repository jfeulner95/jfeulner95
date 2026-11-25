#!/usr/bin/env python3
"""Generates assets/bento.svg – the bento-grid profile card.

Static content lives in PROFILE below. Live stats (contributions, repos,
stars, followers) are fetched from GitHub on every run. Only the standard
library is used, so this runs anywhere with Python 3.8+.

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
}
# ─────────────────────────────────────────────────────────────────────────────

OUT = Path(__file__).resolve().parent.parent / "assets" / "bento.svg"
W, H, GAP = 840, 432, 12


def fetch(url, accept="application/vnd.github+json"):
    headers = {"Accept": accept, "User-Agent": "profile-bento-generator"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as r:
        return r.read().decode("utf-8")


def get_stats(user):
    stats = {"contributions": None, "repos": None, "stars": None, "followers": None, "years": None}
    try:
        u = json.loads(fetch(f"https://api.github.com/users/{user}"))
        stats["repos"], stats["followers"] = u["public_repos"], u["followers"]
        stats["years"] = dt.date.today().year - int(u["created_at"][:4])
        stars, page = 0, 1
        while True:
            repos = json.loads(fetch(f"https://api.github.com/users/{user}/repos?per_page=100&page={page}"))
            stars += sum(r["stargazers_count"] for r in repos)
            if len(repos) < 100:
                break
            page += 1
        stats["stars"] = stars
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


def fmt(n):
    if n is None:
        return "–"
    return f"{n / 1000:.1f}k".replace(".0k", "k") if n >= 1000 else str(n)


def tile(x, y, w, h, glow, delay, body):
    gid = f"g{x}{y}"
    return f"""
  <g class="tile" style="animation-delay:{delay}s">
    <radialGradient id="{gid}" cx="0" cy="0" r="1" gradientUnits="userSpaceOnUse"
        gradientTransform="translate({x} {y}) scale({w * 0.9} {h * 1.1})">
      <stop offset="0" stop-color="{glow}" stop-opacity="0.22"/>
      <stop offset="1" stop-color="{glow}" stop-opacity="0"/>
    </radialGradient>
    <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="20" fill="#0f1117"/>
    <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="20" fill="url(#{gid})"/>
    <rect x="{x + .5}" y="{y + .5}" width="{w - 1}" height="{h - 1}" rx="19.5" fill="none" stroke="#ffffff" stroke-opacity="0.08"/>
    {body}
  </g>"""


def chips(items, x0, y0, max_w, mono=False):
    out, x, y = [], x0, y0
    char_w = 8.2 if mono else 7.6
    for label, color in items:
        w = len(label) * char_w + 38
        if x + w > x0 + max_w:
            x, y = x0, y + 42
        out.append(
            f'<rect x="{x}" y="{y}" width="{w:.0f}" height="32" rx="16" fill="#ffffff" fill-opacity="0.05" '
            f'stroke="#ffffff" stroke-opacity="0.08"/>'
            f'<circle cx="{x + 16}" cy="{y + 16}" r="4.5" fill="{color}"/>'
            f'<text x="{x + 28}" y="{y + 21}" class="chip{" mono" if mono else ""}">{escape(label)}</text>')
        x += w + 8
    return "".join(out)


def build(p, s):
    today = dt.date.today().isoformat()
    col1, row2 = 528, 220 + GAP
    hero = f"""
    <text x="28" y="44" class="eyebrow">{escape(p['greeting'])}</text>
    <text x="28" y="94" class="name">{escape(p['name'])}</text>
    <text x="28" y="128" class="role">{escape(p['role'])}</text>
    <text x="28" y="164" class="bio">{escape(p['bio'][0])}</text>
    <text x="28" y="186" class="bio">{escape(p['bio'][1])}</text>
    <circle cx="{col1 - 150}" cy="40" r="4" fill="#4ade80" class="pulse"/>
    <circle cx="{col1 - 150}" cy="40" r="4" fill="#4ade80"/>
    <text x="{col1 - 138}" y="44" class="status">{escape(p['status'])}</text>"""

    sx, sw = col1 + GAP, W - col1 - GAP
    cells = [("contributions", "contributions · 1y"), ("repos", "public repos"), ("years", "years on GitHub"), ("followers", "followers")]
    stat_body = [f'<text x="{sx + 24}" y="{44}" class="eyebrow">GITHUB · LIVE</text>']
    for i, (key, label) in enumerate(cells):
        cx = sx + 24 + (i % 2) * (sw / 2 - 8)
        cy = 104 + (i // 2) * 74
        stat_body.append(f'<text x="{cx}" y="{cy}" class="num">{fmt(s[key])}</text>'
                         f'<text x="{cx}" y="{cy + 20}" class="label">{label}</text>')
    stat_body.append(f'<text x="{sx + sw - 20}" y="44" class="label" text-anchor="end">{today}</text>')

    lw = 330
    langs = (f'<text x="24" y="{row2 + 38}" class="eyebrow">LANGUAGES</text>'
             + chips(p["languages"], 24, row2 + 60, lw - 40, mono=True))

    tx, tw = lw + GAP, 330
    tools = (f'<text x="{tx + 24}" y="{row2 + 38}" class="eyebrow">PLATFORMS &amp; TOOLS</text>'
             + chips(p["tools"], tx + 24, row2 + 60, tw - 40))

    ex = tx + tw + GAP
    ew = W - ex
    hh = H - row2
    wave_y = row2 + 72
    period = 36
    wave = f"M{ex - period * 2},{wave_y + 18}"
    for i in range(12):
        x = ex - period * 2 + i * period
        wave += f" V{wave_y - 18} H{x + period / 2} V{wave_y + 18} H{x + period}"
    signal = f"""
    <clipPath id="wclip"><rect x="{ex}" y="{row2}" width="{ew}" height="{hh}" rx="20"/></clipPath>
    <text x="{ex + 24}" y="{row2 + 38}" class="eyebrow">SIGNAL</text>
    <g clip-path="url(#wclip)">
      <path d="{wave}" class="wave" stroke="url(#brand)"/>
    </g>
    <text x="{ex + 24}" y="{row2 + hh - 46}" class="big">bits → bots</text>
    <text x="{ex + 24}" y="{row2 + hh - 24}" class="label">embedded meets AI</text>"""

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img"
     aria-label="{escape(p['name'])} – {escape(p['role'])}">
  <defs>
    <linearGradient id="brand" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#38bdf8"/><stop offset="0.5" stop-color="#a78bfa"/><stop offset="1" stop-color="#f472b6"/>
    </linearGradient>
  </defs>
  <style>
    text {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Inter, Helvetica, Arial, sans-serif; fill: #e6e8ee; }}
    .mono {{ font-family: 'SF Mono', 'JetBrains Mono', Menlo, Consolas, monospace; }}
    .eyebrow {{ font-size: 11px; font-weight: 600; letter-spacing: 2px; fill: #8a8f9c; }}
    .name {{ font-size: 42px; font-weight: 800; letter-spacing: -1.2px; }}
    .role {{ font-size: 21px; font-weight: 700; fill: url(#brand); }}
    .bio {{ font-size: 14.5px; fill: #a3a8b4; }}
    .status {{ font-size: 12px; fill: #8a8f9c; }}
    .num {{ font-size: 36px; font-weight: 800; letter-spacing: -1px; }}
    .label {{ font-size: 12px; fill: #8a8f9c; }}
    .chip {{ font-size: 13px; font-weight: 600; fill: #e6e8ee; }}
    .big {{ font-size: 20px; font-weight: 800; letter-spacing: -0.4px; }}
    .wave {{ fill: none; stroke-width: 2.5; stroke-linejoin: round; animation: scroll 1.6s linear infinite; }}
    .tile {{ animation: rise .7s cubic-bezier(.2,.8,.2,1) backwards; }}
    .pulse {{ transform-box: fill-box; transform-origin: center; animation: pulse 2s ease-out infinite; }}
    @keyframes rise {{ from {{ opacity: 0; transform: translateY(14px); }} to {{ opacity: 1; transform: none; }} }}
    @keyframes pulse {{ from {{ transform: scale(1); opacity: .7; }} to {{ transform: scale(3.5); opacity: 0; }} }}
    @keyframes scroll {{ from {{ transform: translateX(0); }} to {{ transform: translateX({period}px); }} }}
  </style>
{tile(0, 0, col1, 220, "#a78bfa", 0.0, hero)}
{tile(sx, 0, sw, 220, "#38bdf8", 0.12, "".join(stat_body))}
{tile(0, row2, lw, H - row2, "#5c9eff", 0.24, langs)}
{tile(tx, row2, tw, H - row2, "#f472b6", 0.36, tools)}
{tile(ex, row2, ew, H - row2, "#4ade80", 0.48, signal)}
</svg>
"""


if __name__ == "__main__":
    stats = get_stats(PROFILE["username"])
    print("stats:", stats)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(PROFILE, stats), encoding="utf-8")
    print(f"wrote {OUT}")
