"""Drive the local PACOS (demo data) and record a storyboard for render_demo.py.

Usage: python capture_demo.py <work_dir> [base_url]

Writes <work>/shots/*.png (2x screenshots) and <work>/storyboard.json: one list
of events per scene. Events (coordinates are CSS px of a 1920x1080 viewport):
  {"t": "state", "img": ..., "fade": s}   show a screenshot (crossfade s)
  {"t": "move", "to": [x, y]}              cursor glides to a point
  {"t": "click"}                           press + ripple
  {"t": "type", "imgs": [...]}            typing frames, shown in sequence
  {"t": "focus", "box": [x, y, w, h], "zoom": z}  camera eases onto a box
  {"t": "wide"}                            camera eases back to the full window
  {"t": "wait", "s": s}
Scene 0 and the last scene are the title and end cards (no events).
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

WORK = Path(sys.argv[1]); SHOTS = WORK / "shots"; SHOTS.mkdir(parents=True, exist_ok=True)
BASE = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:5173"

scenes: list[list[dict]] = [[]]  # scene 0: title card
n = 0


def main():
    global n
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome", headless=True)
        ctx = b.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=2,
                            permissions=["clipboard-read", "clipboard-write"])
        pg = ctx.new_page()
        ev: list[dict] = []

        def snap(fade=0.0, settle=500):
            global n
            pg.wait_for_timeout(settle)
            n += 1
            path = SHOTS / f"{n:03d}.png"
            pg.screenshot(path=str(path))
            ev.append({"t": "state", "img": path.name, "fade": fade})
            return path.name

        def box(loc):
            bb = loc.bounding_box()
            return [bb["x"], bb["y"], bb["width"], bb["height"]]

        def center(loc):
            x, y, w, h = box(loc)
            return [x + w / 2, y + h / 2]

        def move(loc):
            ev.append({"t": "move", "to": center(loc)})

        def focus(loc_or_box, zoom=None):
            bb = loc_or_box if isinstance(loc_or_box, list) else box(loc_or_box)
            e = {"t": "focus", "box": bb}
            if zoom:
                e["zoom"] = zoom
            ev.append(e)

        def type_into(loc, text, step=3):
            global n
            loc.click()
            imgs = []
            for i in range(0, len(text), step):
                loc.press_sequentially(text[i:i + step], delay=0)
                n += 1
                path = SHOTS / f"{n:03d}.png"
                pg.screenshot(path=str(path))
                imgs.append(path.name)
            ev.append({"t": "type", "imgs": imgs})

        def new_scene():
            nonlocal ev
            ev = []
            scenes.append(ev)

        def ask(text):
            box_ = pg.locator("textarea.chat-input")
            focus(box_, zoom=1.9)
            move(box_); ev.append({"t": "click"})
            type_into(box_, text)
            send = pg.get_by_role("button", name="Send")
            move(send); ev.append({"t": "click"})
            send.click()
            snap(fade=0.15, settle=400)  # "Thinking…"
            ev.append({"t": "wide"})
            pg.get_by_text("Thinking…").wait_for(state="detached", timeout=240_000)
            pg.wait_for_timeout(600)

        # ── 1. chat home → type a question ────────────────────────────────
        new_scene()
        pg.goto(BASE + "/"); pg.wait_for_load_state("networkidle")
        snap(fade=0.0)
        ev.append({"t": "wait", "s": 0.6})
        ask("Who should I follow up with this week?")

        # ── 2. follow-up answer ─────────────────────────────────────────────
        new_scene()
        pg.evaluate("document.querySelector('.chat-scroll')?.scrollTo(0, 0)")
        snap(fade=0.35)
        card = pg.locator(".record-card").first
        focus(card, zoom=1.7)
        chase = card.get_by_text("Chase now").first
        move(chase)
        ev.append({"t": "wait", "s": 1.6})
        ev.append({"t": "wide"})

        # ── 3. a draft from the CV ────────────────────────────────────────
        new_scene()
        nc = pg.get_by_role("button", name="New chat").first
        move(nc); ev.append({"t": "click"}); nc.click()
        pg.wait_for_load_state("networkidle")
        snap(fade=0.25)
        ask("Draft a short LinkedIn DM to Asha Verma at Northwind Labs")
        snap(fade=0.35)
        draft = pg.locator(".draft-card").first
        focus(draft, zoom=1.8)
        copy = draft.get_by_role("button", name="Copy")
        move(copy); ev.append({"t": "click"}); copy.click()
        snap(fade=0.15, settle=250)

        # ── 4. report a reply, apply the proposed update ─────────────────
        new_scene()
        ev.append({"t": "wide"})
        move(nc); ev.append({"t": "click"}); nc.click()
        pg.wait_for_load_state("networkidle")
        snap(fade=0.25)
        ask("Priya Shah from Lumen Health replied, she wants an interview next week")
        snap(fade=0.35)
        prop = pg.locator(".change-card").first
        focus(prop, zoom=1.6)
        apply_ = pg.get_by_role("button", name="Apply").first
        move(apply_); ev.append({"t": "click"}); apply_.click()
        snap(fade=0.2, settle=1200)

        # ── 5. My people: the board ──────────────────────────────────────
        new_scene()
        ev.append({"t": "wide"})
        link = pg.get_by_role("link", name="My people")
        move(link); ev.append({"t": "click"}); link.click()
        pg.wait_for_load_state("networkidle")
        snap(fade=0.3)
        heads = pg.locator(".kb-col-head")
        for i in range(heads.count()):
            focus(heads.nth(i), zoom=2.2)
            move(heads.nth(i))
            ev.append({"t": "wait", "s": 0.35})
        ev.append({"t": "wide"})

        # ── 6. To write: batch writing ─────────────────────────────────────
        new_scene()
        col = pg.locator(".kb-col").first
        focus(col, zoom=1.45)
        batch = col.locator(".kb-more").first
        move(batch)
        ev.append({"t": "wait", "s": 1.2})
        card = col.get_by_text("Asha Verma").first
        move(card)
        ev.append({"t": "wait", "s": 1.0})

        # ── 7. Ready to send: open, read, copy, mark sent ─────────────────
        new_scene()
        ev.append({"t": "wide"})
        sana = pg.get_by_text("Sana Qureshi").first
        move(sana); ev.append({"t": "click"}); sana.click()
        snap(fade=0.3, settle=900)
        drawer = pg.locator(".drawer")
        likely = drawer.get_by_text("Likely", exact=True).first
        focus([likely.bounding_box()["x"] - 20, likely.bounding_box()["y"] - 60, 640, 120], zoom=2.0)
        move(likely)
        ev.append({"t": "wait", "s": 1.0})
        focus(drawer, zoom=1.3)
        dm = drawer.get_by_text("LinkedIn DM", exact=True).first
        move(dm); ev.append({"t": "click"}); dm.click()
        snap(fade=0.2, settle=500)
        copy2 = drawer.get_by_role("button", name="Copy").last
        move(copy2); ev.append({"t": "click"}); copy2.click()
        snap(fade=0.15, settle=250)
        sent = drawer.get_by_role("button", name="Sent by DM").first
        focus(sent, zoom=2.0)
        move(sent); ev.append({"t": "click"}); sent.click()
        snap(fade=0.25, settle=900)

        # ── 8. Waiting + follow-ups ──────────────────────────────────────
        new_scene()
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(400)
        snap(fade=0.3)
        ev.append({"t": "wide"})
        wcol = pg.locator(".kb-col").nth(2)
        focus(wcol, zoom=1.5)
        tara = wcol.get_by_text("Tara Fernandes").first
        move(tara)
        ev.append({"t": "wait", "s": 0.6})
        ev.append({"t": "click"}); tara.click()
        snap(fade=0.3, settle=900)
        nxt = pg.locator(".drawer .next-step").first
        focus(nxt, zoom=1.9)
        for name in ["They’re interested", "Asked to follow up", "Rejected", "Remind me"]:
            btn = nxt.get_by_role("button", name=name).first
            if btn.count():
                move(btn)
                ev.append({"t": "wait", "s": 0.3})
        pg.keyboard.press("Escape")
        pg.wait_for_timeout(400)

        # ── 9. Search + check inbox ──────────────────────────────────────
        new_scene()
        snap(fade=0.25)
        ev.append({"t": "wide"})
        search = pg.get_by_placeholder("Search by name or company")
        focus([search.bounding_box()["x"] - 40, 20, 560, 70], zoom=2.2)
        move(search); ev.append({"t": "click"})
        type_into(search, "Lumen", step=1)
        ev.append({"t": "wide"})
        ev.append({"t": "wait", "s": 0.8})
        inbox = pg.get_by_role("button", name="Check inbox")
        focus([search.bounding_box()["x"] - 40, 20, 560, 70], zoom=2.2)
        move(inbox)
        ev.append({"t": "wait", "s": 1.0})
        search.fill("")

        # ── 10. Find people: the form ────────────────────────────────────
        new_scene()
        ev.append({"t": "wide"})
        link = pg.get_by_role("link", name="Find people")
        move(link); ev.append({"t": "click"}); link.click()
        pg.wait_for_load_state("networkidle")
        snap(fade=0.3)
        comp = pg.get_by_placeholder("Company")
        focus([520, 140, 1130, 50], zoom=1.7)
        move(comp); ev.append({"t": "click"})
        type_into(comp, "Northwind Labs", step=2)
        pg.keyboard.press("Escape")
        role = pg.get_by_placeholder("Role (optional)")
        move(role); ev.append({"t": "click"})
        type_into(role, "ML Engineer", step=3)
        pg.keyboard.press("Escape")
        city = pg.get_by_placeholder("Location (optional)")
        move(city); ev.append({"t": "click"})
        type_into(city, "Bengaluru", step=3)
        pg.keyboard.press("Escape")
        build = pg.get_by_role("button", name="Build searches")
        move(build); ev.append({"t": "click"}); build.click()
        pg.locator(".disc-grid").wait_for(timeout=30_000)
        snap(fade=0.35)

        # ── 11. the search cards ─────────────────────────────────────────
        new_scene()
        ev.append({"t": "wide"})
        cards = pg.locator(".disc-grid > *")
        focus(cards.nth(0), zoom=1.9)
        move(cards.nth(0).locator(".tag").first)
        ev.append({"t": "wait", "s": 0.8})
        for lbl in ["LinkedIn", "Google", "Copy query"]:
            move(cards.nth(0).get_by_text(lbl, exact=True).first)
            ev.append({"t": "wait", "s": 0.45})
        ev.append({"t": "focus", "box": [520, 640, 1130, 210], "zoom": 1.5})
        move(cards.nth(3))
        ev.append({"t": "wait", "s": 1.2})

        # ── 12. Find and import ──────────────────────────────────────────
        new_scene()
        ev.append({"t": "wide"})
        imp = pg.locator(".disc-enrich")
        focus(imp, zoom=1.55)
        fi = imp.get_by_role("button", name="Find and import")
        move(fi)
        ev.append({"t": "wait", "s": 1.6})
        paste = imp.get_by_role("button", name="Paste results instead")
        move(paste); ev.append({"t": "click"}); paste.click()
        snap(fade=0.25, settle=500)
        focus(pg.locator(".disc-enrich"), zoom=1.5)
        move(pg.get_by_placeholder("Paste the Google results page here"))
        ev.append({"t": "wait", "s": 1.0})

        # ── 13. my CV ─────────────────────────────────────────────────────
        new_scene()
        ev.append({"t": "wide"})
        link = pg.get_by_role("link", name="My CV")
        move(link); ev.append({"t": "click"}); link.click()
        pg.wait_for_load_state("networkidle")
        snap(fade=0.3)
        cv = pg.get_by_text("Data Scientist").first
        move(cv); ev.append({"t": "click"}); cv.click()
        snap(fade=0.25, settle=600)
        ev.append({"t": "focus", "box": [520, 160, 1130, 520], "zoom": 1.5})
        ev.append({"t": "wait", "s": 1.2})
        ev.append({"t": "wide"})

        scenes.append([])  # end card
        b.close()

    (WORK / "storyboard.json").write_text(json.dumps(scenes, indent=1))
    print("scenes:", len(scenes), "shots:", n)


main()
