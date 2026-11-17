"""Turn storyboard.json + narration into the intro video, rendered by stage.html.

Usage: python build_demo.py <capture_work_dir> <voice_dir> <out.mp4> [--preview SECONDS]

Python lays out the timeline (when each state shows, where the cursor and the
camera go); stage.html draws a frame for any time t; Playwright seeks through
every frame and pipes it to ffmpeg. Seeking (not playing) keeps it smooth no
matter how slow a frame is to draw.
"""
import json
import math
import re
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from script import SCENES  # noqa: E402

FF = imageio_ffmpeg.get_ffmpeg_exe()
HERE = Path(__file__).parent
WORK, VOICE, OUT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
PREVIEW = float(sys.argv[sys.argv.index("--preview") + 1]) if "--preview" in sys.argv else None
FPS = 30

# window geometry in the 1920x1080 world; app screenshots are 1920x1080 CSS px
S = 0.82
BAR = 30
WW, WH = 1920 * S, 1080 * S
WX, WY = (1920 - WW) / 2, (1080 - WH - BAR) / 2

# durations (s): one palette — quick 0.15, standard 0.65, slow 1.0
CAM_DUR, WIDE_DUR, TYPE_FRAME, HOVER, CLICK_HOLD = 1.0, 0.9, 0.11, 0.14, 0.26
LEAD, TAIL = 0.3, 0.5


def world(pt):
    return [WX + pt[0] * S, WY + BAR + pt[1] * S]


def dur(path):
    r = subprocess.run([FF, "-hide_banner", "-i", str(path), "-f", "null", "-"], capture_output=True, text=True)
    h, m, s = re.findall(r"time=(\d+):(\d+):([\d.]+)", r.stderr)[-1]
    return int(h) * 3600 + int(m) * 60 + float(s)


def clamp_cam(z, x, y):
    hw, hh = 960 / z, 540 / z
    return {"z": z, "x": min(max(x, hw), 1920 - hw), "y": min(max(y, hh), 1080 - hh)}


def compile_timeline():
    board = json.loads((WORK / "storyboard.json").read_text())
    assert len(board) == len(SCENES), (len(board), len(SCENES))
    shots = (WORK / "shots").resolve()
    tl = {"win": {"x": WX, "y": WY, "w": WW, "h": WH, "bar": BAR},
          "states": [], "camera": [], "cursor": [], "clicks": [], "captions": [], "cards": [],
          "camInit": {"z": 1, "x": 960, "y": 540}}
    audio = []
    cam = dict(tl["camInit"])
    cur = [1500.0, 1150.0]
    tl["cursorInit"] = list(cur)

    def cam_to(t0, target, d):
        nonlocal cam
        tl["camera"].append({"t0": t0, "t1": t0 + d, "from": dict(cam), "to": target})
        cam = target

    T = 0.0
    n_app = 0
    for i, ((kind, caption, _), events) in enumerate(zip(SCENES, board)):
        vd = dur(VOICE / f"{i:02d}.mp3")
        audio.append((T + LEAD, VOICE / f"{i:02d}.mp3"))
        if kind in ("title", "end"):
            L = LEAD + vd + 0.9
            tl["cards"].append({"id": kind, "t0": T + (0.15 if kind == "end" else 0), "t1": T + L + (1 if kind == "end" else 0),
                                "inDur": 0.7, "outDur": 0.45})
            if kind == "title":
                tl["window"] = {"in": T + L - 0.25, "inDur": 0.8}
                tl["cursorVis"] = {"in": T + L + 0.5}
            else:
                tl["window"].update({"out": T - 0.1, "outDur": 0.45})
                tl["cursorVis"]["out"] = T - 0.25
            T += L
            continue

        n_app += 1
        c = T + 0.35
        for e in events:
            k = e["t"]
            if k == "state":
                tl["states"].append({"t": c, "img": (shots / e["img"]).as_uri(), "fade": e["fade"]})
                c += max(e["fade"], 0.12)
            elif k == "move":
                to = world(e["to"])
                d = min(1.0, max(0.5, 0.42 + math.dist(cur, to) / 1700))
                tl["cursor"].append({"t0": c, "t1": c + d, "from": list(cur), "to": to})
                cur = to
                c += d + HOVER
            elif k == "click":
                tl["clicks"].append({"t": c, "at": list(cur)})
                c += CLICK_HOLD
            elif k == "type":
                for img in e["imgs"]:
                    tl["states"].append({"t": c, "img": (shots / img).as_uri(), "fade": 0})
                    c += TYPE_FRAME
                c += 0.2
            elif k == "focus":
                x, y, w, h = e["box"]
                (wx, wy), bw, bh = world([x, y]), w * S, h * S
                fit = min(1920 * 0.82 / max(bw, 1), 1080 * 0.74 / max(bh, 1))
                z = max(1.0, min(e.get("zoom", 2.0), fit, 2.4))
                cam_to(c, clamp_cam(z, wx + bw / 2, wy + bh / 2), CAM_DUR)
                c += 0.2
            elif k == "wide":
                cam_to(c, dict(tl["camInit"]), WIDE_DUR)
                c += 0.15
            elif k == "wait":
                c += e["s"]
        L = max(c - T + 0.5, LEAD + vd + TAIL)
        tl["captions"].append({"t0": T + 0.2, "t1": T + L - 0.1, "n": f"{n_app:02d}", "text": caption})
        T += L
    tl["total"] = T
    return tl, audio


def render(tl, audio):
    total = PREVIEW or tl["total"]
    frames = int(total * FPS)
    silent = OUT.with_suffix(".video.mp4")
    enc = subprocess.Popen([FF, "-hide_banner", "-loglevel", "error", "-y", "-f", "image2pipe",
                            "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
                            "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p",
                            str(silent)], stdin=subprocess.PIPE)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        pg.goto((HERE / "stage.html").resolve().as_uri(), wait_until="networkidle")
        pg.evaluate("document.fonts.ready")
        pg.evaluate("tl => load(tl)", tl)
        for f in range(frames):
            pg.evaluate(f"seek({f / FPS})")
            enc.stdin.write(pg.screenshot(type="jpeg", quality=94))
            if f % 300 == 0:
                print(f"frame {f}/{frames}", flush=True)
        b.close()
    enc.stdin.close()
    enc.wait()

    # narration: each scene's voice placed at its start, mixed, normalised
    ins, flt = [], []
    for k, (t, mp3) in enumerate(audio):
        if t >= total:
            break
        ins += ["-i", str(mp3)]
        flt.append(f"[{k + 1}:a]aresample=48000,adelay={int(t * 1000)}:all=1[a{k}]")
    n = len(flt)
    mix = "".join(f"[a{k}]" for k in range(n)) + f"amix=inputs={n}:normalize=0,apad,atrim=0:{total},loudnorm=I=-16:TP=-1.5:LRA=11[aout]"
    subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-y", "-i", str(silent), *ins,
                    "-filter_complex", ";".join(flt) + ";" + mix,
                    "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
                    "-ar", "48000", "-movflags", "+faststart", "-shortest", str(OUT)], check=True)
    silent.unlink()


if __name__ == "__main__":
    tl, audio = compile_timeline()
    (WORK / "timeline.json").write_text(json.dumps(tl, indent=1))
    print(f"timeline: {tl['total']:.1f}s, {len(tl['states'])} states, {len(tl['clicks'])} clicks")
    render(tl, audio)
    print("built", OUT)
