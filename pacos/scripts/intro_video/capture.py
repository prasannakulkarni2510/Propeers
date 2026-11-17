"""Capture 1920x1080 frames of the running local PACOS (demo data) for the video."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
BASE = "http://localhost:5173"
only = set(sys.argv[2:])


def want(n):
    return not only or n in only


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)
    pg = b.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)

    def shot(name):
        pg.wait_for_timeout(700)
        pg.screenshot(path=str(OUT / f"{name}.png"))
        print("shot", name, flush=True)

    def ask(text, wait_for):
        box = pg.locator("textarea.chat-input")
        box.fill(text)
        pg.get_by_role("button", name="Send").click()
        pg.wait_for_timeout(1000)
        pg.get_by_text("Thinking…").wait_for(state="detached", timeout=240_000)
        pg.locator(wait_for).last.wait_for(timeout=60_000)
        pg.wait_for_timeout(1500)

    if want("chat"):
        pg.goto(BASE + "/"); pg.wait_for_load_state("networkidle"); shot("01-chat-hero")
        ask("Who should I follow up with this week?", ".chat-msg.assistant")
        shot("02-chat-followups")
        pg.goto(BASE + "/"); pg.wait_for_load_state("networkidle")
        ask("Draft a short LinkedIn DM to Asha Verma at Northwind Labs", ".draft-card")
        shot("03-chat-draft")
        pg.goto(BASE + "/"); pg.wait_for_load_state("networkidle")
        ask("Priya Shah from Lumen Health replied, she wants an interview next week", ".chat-msg.assistant")
        shot("04-chat-update")

    if want("pipeline"):
        pg.goto(BASE + "/pipeline"); pg.wait_for_load_state("networkidle"); shot("05-pipeline")
        pg.get_by_text("Priya Shah").first.click(); pg.wait_for_timeout(1200); shot("06-lead-panel")
        pg.keyboard.press("Escape")
        pg.goto(BASE + "/pipeline"); pg.wait_for_load_state("networkidle")
        pg.get_by_text("Sana Qureshi").first.click(); pg.wait_for_timeout(1200); shot("07-lead-drafts")

    if want("find"):
        pg.goto(BASE + "/find"); pg.wait_for_load_state("networkidle")
        pg.get_by_placeholder("Company").fill("Northwind Labs")
        pg.get_by_placeholder("Role (optional)").fill("Machine Learning Engineer")
        pg.get_by_placeholder("Location (optional)").fill("Bengaluru")
        pg.keyboard.press("Escape")
        pg.get_by_role("button", name="Build searches").click()
        pg.locator(".disc-grid").wait_for(timeout=30_000); shot("08-find")

    if want("cv"):
        pg.goto(BASE + "/cv"); pg.wait_for_load_state("networkidle")
        pg.get_by_text("Data Scientist").first.click(); shot("09-cv")

    if want("about"):
        pg.goto(BASE + "/about"); pg.wait_for_load_state("networkidle"); shot("10-about")
        pg.screenshot(path=str(OUT / "about-full.png"), full_page=True)
    b.close()
