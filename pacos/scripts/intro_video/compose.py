"""Render each scene as a designed 1920x1080 still: caption + framed app screenshot."""
import base64
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from script import SCENES  # noqa: E402

FRAMES = Path(sys.argv[1]); OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)

HEAD = """<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;700&family=Source+Serif+4:opsz,wght@8..60,500;8..60,600&display=swap" rel="stylesheet">
<style>
:root{--bg:oklch(96.6% 0.008 60);--text:oklch(21% 0.012 38);--muted:oklch(47% 0.013 45);--brand:oklch(61% 0.2 33);--line:oklch(87% 0.009 55)}
*{margin:0;box-sizing:border-box}
body{width:1920px;height:1080px;background:var(--bg);color:var(--text);font-family:Geist,sans-serif;overflow:hidden;position:relative}
.glow{position:absolute;inset:0;background:radial-gradient(1200px 600px at 85% -10%,oklch(88% 0.06 35 / .55),transparent 70%)}
.cap{position:absolute;left:120px;top:64px;display:flex;align-items:baseline;gap:28px}
.n{font-size:22px;font-weight:500;color:var(--brand);letter-spacing:.08em}
.t{font-family:"Source Serif 4",serif;font-weight:600;font-size:54px;letter-spacing:-.01em}
.shot{position:absolute;left:120px;top:170px;width:1680px;height:945px;border-radius:18px;overflow:hidden;
 border:1px solid var(--line);box-shadow:0 30px 80px -20px oklch(30% 0.03 40 / .35),0 8px 24px -8px oklch(30% 0.03 40 / .2)}
.shot img{width:100%;display:block}
.card{position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;padding:0 200px}
.wm{font-weight:700;font-size:140px;letter-spacing:.01em;line-height:1}
.wm span{color:var(--brand)}
.sub{font-family:"Source Serif 4",serif;font-size:64px;font-weight:500;margin-top:36px;max-width:22ch;line-height:1.15}
.small{margin-top:40px;font-size:30px;color:var(--muted)}
</style></head><body><div class="glow"></div>"""


def scene_html(i, frame, caption):
    if frame == "title":
        return HEAD + """<div class="card"><div class="wm">PAC<span>OS</span></div>
<div class="sub">Personal AI Career Operating System</div>
<div class="small">Drafts your job-search outreach. Tracks every reply. Never sends.</div></div></body></html>"""
    if frame == "end":
        return HEAD + """<div class="card"><div class="wm">PAC<span>OS</span></div>
<div class="sub">It drafts. You decide. You send.</div>
<div class="small">Chat &nbsp;·&nbsp; My people &nbsp;·&nbsp; Find people &nbsp;·&nbsp; My CV</div></div></body></html>"""
    img = base64.b64encode((FRAMES / f"{frame}.png").read_bytes()).decode()
    return HEAD + f"""<div class="cap"><span class="n">{i:02d}</span><span class="t">{caption}</span></div>
<div class="shot"><img src="data:image/png;base64,{img}"></div></body></html>"""


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)
    pg = b.new_page(viewport={"width": 1920, "height": 1080})
    for i, (frame, caption, _) in enumerate(SCENES):
        pg.set_content(scene_html(i, frame, caption), wait_until="networkidle")
        pg.evaluate("document.fonts.ready")
        pg.wait_for_timeout(300)
        pg.screenshot(path=str(OUT / f"{i:02d}.png"))
        print("composed", i, flush=True)
    b.close()
