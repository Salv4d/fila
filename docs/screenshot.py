#!/usr/bin/env python3
"""Regenerates docs/screenshot.png: builds a throwaway demo project, runs real `fila` commands
with colors on, turns the ANSI output into a terminal-looking HTML page and screenshots it.

    python3 -m pip install playwright && python3 -m playwright install chromium
    python3 docs/screenshot.py
"""
import html
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).resolve().parent
FILA = AQUI.parent / "fila"
CORES = {"31": "#ff7b72", "32": "#7ee787", "33": "#e3b341", "36": "#79c0ff", "2": "#8b949e"}


def sh(cwd, *args):
    env = {**os.environ, "FORCE_COLOR": "1", "FILA_ROOT": str(cwd)}
    return subprocess.run([sys.executable, str(FILA), *args], cwd=cwd, env=env, capture_output=True, text=True).stdout


def ansi_html(s):
    out, abertos = [], 0
    for parte in re.split(r"(\x1b\[[\d;]*m)", s):
        m = re.fullmatch(r"\x1b\[([\d;]*)m", parte)
        if not m:
            out.append(html.escape(parte)); continue
        cod = m[1]
        if cod in ("0", ""):
            out.append("</span>" * abertos); abertos = 0
        elif cod == "1":
            out.append('<span style="font-weight:700;color:#f0f6fc">'); abertos += 1
        elif cod in CORES:
            out.append(f'<span style="color:{CORES[cod]}">'); abertos += 1
    return "".join(out) + "</span>" * abertos


def main():
    with tempfile.TemporaryDirectory() as t:
        d = Path(t) / "my-video"
        d.mkdir()
        sh(d, "init")
        mig = d / ".fila" / "migrations"
        arquivos = {
            "20261114223000_transcribe_raw.sh": "#!/usr/bin/env bash\n# Transcribe the raw recording\ntrue\n",
            "20261114223500_render_animations.sh": "#!/usr/bin/env bash\n# Render the 6 animations in 1080p60\ntrue\n",
            "20261114224000_render_final_cut.sh": "#!/usr/bin/env bash\n# Render the final cut with b-roll and music\ntrue\n",
            "20261114224500_review_subtitles.md": "# Review the subtitles before publishing\n",
            "20261114225000_upload_thumbnail.md": "# Pick the thumbnail frame and upload\n",
        }
        for nome, corpo in arquivos.items():
            (mig / nome).write_text(corpo)
        sh(d, "run", "20261114223000")
        status = sh(d, "status").replace(str(d), "~/my-video")
        hook = sh(d, "hook").replace(str(d), "~/my-video")
    import json
    ctx = json.loads(hook)["hookSpecificOutput"]["additionalContext"]
    corpo = (f'<span style="color:#8b949e">$</span> fila status\n{ansi_html(status)}\n'
             f'<span style="color:#8b949e">$ # what Claude Code sees when a session starts (SessionStart hook)</span>\n'
             f'<span style="color:#d2a8ff">{html.escape(ctx)}</span>')
    pagina = f"""<!doctype html><meta charset="utf-8"><style>
    body {{ margin:0; background:#0b0e14; padding:28px; font:15px/1.55 'JetBrains Mono','DejaVu Sans Mono',monospace; }}
    .janela {{ background:#0d1117; border:1px solid #30363d; border-radius:12px; overflow:hidden; width:1080px;
               box-shadow:0 20px 60px #0008; }}
    .barra {{ background:#161b22; padding:10px 14px; display:flex; gap:8px; align-items:center; color:#8b949e; font-size:13px; }}
    .barra i {{ width:12px; height:12px; border-radius:50%; display:inline-block; }}
    pre {{ margin:0; padding:18px 22px 22px; color:#c9d1d9; white-space:pre-wrap; }}
    </style><div class="janela"><div class="barra"><i style="background:#ff5f56"></i><i style="background:#ffbd2e"></i>
    <i style="background:#27c93f"></i><span style="margin-left:10px">~/my-video</span></div><pre>{corpo}</pre></div>"""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1140, "height": 400}, device_scale_factor=2)
        pg.set_content(pagina)
        pg.locator(".janela").screenshot(path=str(AQUI / "screenshot.png"))
        b.close()
    print(AQUI / "screenshot.png")


if __name__ == "__main__":
    main()
