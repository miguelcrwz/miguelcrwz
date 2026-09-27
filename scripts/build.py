"""Builds the profile README: an info panel in GitHub's own colors (one SVG per
theme) with an Email button under it. README.md is generated too, so edit the
settings below instead of editing it by hand.

Runs daily through .github/workflows/profile.yml to keep "Uptime" current.
To run it locally:

    pip install -r scripts/requirements.txt
    python scripts/build.py
"""

import base64
import calendar
import datetime as dt
import functools
import io
import pathlib
import urllib.request
from html import escape

from fontTools import subset

USER = "miguelcrwz"
EMAIL = "miguwlcrwz@gmail.com"
SINCE = dt.date(2023, 11, 8)  # GitHub account creation

INFO = [
    ("Role", "Back-End Engineer"),
    ("Stack", "C#, .NET, SQL Server, Azure"),
    ("AI", "Claude Code, agents & MCP"),
    ("Location", "Rio de Janeiro, Brazil"),
    ("Uptime", "{uptime}"),
]

# GitHub's Primer colors, so the panel reads as part of the profile page
THEMES = {
    "dark": dict(border="#3d444d", accent="#4493f8", fg="#f0f6fc", muted="#9198a1"),
    "light": dict(border="#d1d9e0", accent="#0969da", fg="#1f2328", muted="#59636e"),
}
# The Email button sits inside a link, and GitHub only swaps themed images when the
# <img> is a direct child of <picture>. So the button is one transparent SVG for both
# themes: mid-tone text that reads on white and on #0d1117 (~4.4:1 on each), and a
# translucent border that lands on each theme's own border colour.
NEUTRAL = dict(border="rgba(141,153,167,.375)", accent="#2c78db", fg="#2c78db", muted="#727982")

ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

MONO = "Consolas, InconsolataEmbed, monospace"
FONT_URL = "https://cdn.jsdelivr.net/npm/@fontsource/inconsolata@5/files/inconsolata-latin-{}-normal.woff2"

W, PAD = 800, 24
SIZE, LH = 16, 26
ADV = SIZE * 0.55                   # Consolas advance is 0.55em; Inconsolata is scaled to match
LINE = int((W - 2 * PAD) / ADV)     # chars per line, so values end at the right padding
BUTTON_H = 50


def uptime(start: dt.date, end: dt.date) -> str:
    months = (end.year - start.year) * 12 + end.month - start.month - (end.day < start.day)
    y, m = divmod(start.month - 1 + months, 12)
    year, month = start.year + y, m + 1
    anchor = dt.date(year, month, min(start.day, calendar.monthrange(year, month)[1]))
    days = (end - anchor).days
    years, months = divmod(months, 12)
    parts = [(years, "year"), (months, "month"), (days, "day")]
    return ", ".join(f"{n} {unit}{'s' if n != 1 else ''}" for n, unit in parts)


# --------------------------------------------------------------------------- svg

@functools.cache
def font_face(weight: int) -> str:
    with urllib.request.urlopen(FONT_URL.format(weight)) as r:
        font = subset.load_font(io.BytesIO(r.read()), subset.Options())
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = []
    sub = subset.Subsetter(opts)
    sub.populate(unicodes=range(0x20, 0x7F))
    sub.subset(font)
    buf = io.BytesIO()
    subset.save_font(font, buf, opts)
    data = base64.b64encode(buf.getvalue()).decode()
    # size-adjust makes Inconsolata's 0.5em advance match Consolas' 0.55em
    return (f"@font-face{{font-family:InconsolataEmbed;font-weight:{weight};size-adjust:110%;"
            f"src:url(data:font/woff2;base64,{data}) format('woff2');}}")


def svg(w, h, label, body) -> str:
    css = font_face(400) + font_face(700) + f"text{{font-family:{MONO};white-space:pre;font-variant-ligatures:none}}"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'role="img" aria-label="{escape(label)}"><title>{escape(label)}</title>'
            f"<defs><style>{css}</style></defs>{body}</svg>\n")


def text(x, y, spans, anchor=None):
    inner = []
    for s, fill, bold in spans:
        weight = ' font-weight="700"' if bold else ""
        inner.append(f'<tspan fill="{fill}"{weight}>{escape(s)}</tspan>')
    extra = f' text-anchor="{anchor}"' if anchor else ""
    return f'<text x="{x:g}" y="{y:g}" font-size="{SIZE}"{extra}>{"".join(inner)}</text>'


def frame(h, t) -> str:
    return f'<rect x=".5" y=".5" width="{W - 1}" height="{h - 1}" rx="6" fill="none" stroke="{t["border"]}"/>'


def field(key: str, value: str, width: int, t: dict):
    dots = width - len(key) - len(value) - 5  # ". " + ":" + two spaces
    return [(". ", t["accent"], True), (f"{key}:", t["muted"], False),
            (" " + "." * dots + " ", t["border"], False), (value, t["fg"], False)]


def panel(t: dict) -> str:
    title_y = PAD + 14
    label = f"{USER}@github"
    end = PAD + 15 + len(label) * ADV + 8
    body = [f'<rect x="{PAD}" y="{title_y - 5}" width="10" height="1" fill="{t["border"]}"/>',
            text(PAD + 15, title_y, [(USER, t["accent"], True), ("@github", t["muted"], False)]),
            f'<rect x="{end:g}" y="{title_y - 5}" width="{W - PAD - end:g}" height="1" fill="{t["border"]}"/>']
    y = title_y + LH + 6
    stats = {"uptime": uptime(SINCE, dt.date.today())}
    for key, value in INFO:
        body.append(text(PAD, y, field(key, value.format(**stats), LINE, t)))
        y += LH
    h = y - LH + PAD
    alt = "; ".join(f"{k}: {v.format(**stats)}" for k, v in INFO)
    return svg(W, h, f"{USER}@github. {alt}", frame(h, t) + "".join(body))


def email_button(t: dict) -> str:
    y = BUTTON_H / 2 + SIZE * 0.35
    body = (frame(BUTTON_H, t)
            + text(PAD, y, field("Email", EMAIL, LINE - 3, t))
            + text(W - PAD, y, [("->", t["accent"], True)], anchor="end"))
    return svg(W, BUTTON_H, f"Email: {EMAIL}", body)


def readme() -> str:
    alt = f"{USER}@github. " + "; ".join(f"{k}: {v}" for k, v in INFO if "{" not in v)
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="assets/profile-dark.svg" />'
            f'<img src="assets/profile-light.svg" width="100%" alt="{escape(alt)}" /></picture>'
            f'<a href="mailto:{EMAIL}"><img src="assets/email.svg" width="100%" alt="Email: {EMAIL}" /></a>\n')


if __name__ == "__main__":
    ASSETS.mkdir(exist_ok=True)
    outputs = {ROOT / "README.md": readme(), ASSETS / "email.svg": email_button(NEUTRAL)}
    for theme, colors in THEMES.items():
        outputs[ASSETS / f"profile-{theme}.svg"] = panel(colors)
    for path, content in outputs.items():
        path.write_text(content, encoding="utf-8")
    print(", ".join(p.name for p in outputs))
