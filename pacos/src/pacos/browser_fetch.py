"""Fetch Google X-Ray results with a real headless browser (Playwright).

The plain urllib fetch in `enrichment.fetch_xray` is usually answered with a
consent/CAPTCHA wall because Google detects scripted requests. A real Chromium
instance passes most of those checks, so Discovery's auto-import can collect
results without the operator pasting anything.

Optional capability: playwright is NOT in the base requirements (Chromium is
hundreds of MB and does not fit the Render free tier). When the package or the
browser binary is missing, callers fall back to the urllib fetch and then to
the operator paste, exactly as before. To enable locally:

    pip install playwright
    playwright install chromium
"""
from __future__ import annotations

from functools import lru_cache

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# Phrases that identify a Google block/consent page instead of results.
_BLOCK_MARKERS = (
    "unusual traffic", "consent.google.com", "recaptcha",
    "our systems have detected", "before you continue to google",
)


class BrowserFetchError(RuntimeError):
    """Playwright is unusable (missing browser binary, launch failure)."""


@lru_cache(maxsize=1)
def browser_available() -> bool:
    """True when the playwright package is importable. The browser binary is
    only checked at launch time (fetch_xray_browser raises if it's missing)."""
    try:
        import playwright.sync_api  # noqa: F401
    except ImportError:
        return False
    return True


def looks_blocked(html: str) -> bool:
    """Heuristic: is this a consent/CAPTCHA wall rather than a results page?"""
    low = html.lower()
    return any(marker in low for marker in _BLOCK_MARKERS)


def fetch_xray_browser(urls: list[str], *, timeout_ms: int = 15000,
                       ) -> tuple[dict[str, str], list[str]]:
    """GET each X-Ray URL in one headless Chromium session.

    Returns (html_by_url, warnings). URLs that fail or hit a block page are
    reported in warnings and omitted from the result, so the caller can retry
    them with the urllib fetch or leave them to the operator-paste fallback.

    Raises BrowserFetchError when the browser itself can't start (playwright
    not installed, `playwright install chromium` never run, sandbox issues).
    """
    if not browser_available():
        raise BrowserFetchError("playwright is not installed")

    from playwright.sync_api import Error as PlaywrightError
    from playwright.sync_api import sync_playwright

    html_by_url: dict[str, str] = {}
    warnings: list[str] = []
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except PlaywrightError as e:
            # Most common cause: the Chromium binary was never downloaded.
            raise BrowserFetchError(
                "Chromium could not start; run `playwright install chromium` "
                f"once to enable browser fetch ({str(e).splitlines()[0]})"
            ) from e
        try:
            context = browser.new_context(user_agent=_UA, locale="en-US",
                                          viewport={"width": 1280, "height": 900})
            # Pre-answer Google's "before you continue" cookie interstitial so a
            # fresh browser lands on results instead of the consent wall. This
            # only dismisses the cookie prompt; it is not a CAPTCHA bypass.
            context.add_cookies([
                {"name": "SOCS", "value": "CAESEwgDEgk0ODE3Nzk3MjQaAmVuIAEaBgiA_LyaBg",
                 "domain": ".google.com", "path": "/"},
                {"name": "CONSENT", "value": "PENDING+987",
                 "domain": ".google.com", "path": "/"},
            ])
            page = context.new_page()
            for url in urls:
                try:
                    page.goto(url, wait_until="domcontentloaded",
                              timeout=timeout_ms)
                    # Give the results a moment to render; absence of profile
                    # links is fine (zero results is a valid answer).
                    try:
                        page.wait_for_selector('a[href*="linkedin.com/in"]',
                                               timeout=4000)
                    except PlaywrightError:
                        pass
                    html = page.content()
                except PlaywrightError as e:
                    warnings.append(
                        f"browser fetch failed ({str(e).splitlines()[0]})")
                    continue
                if looks_blocked(html):
                    warnings.append(
                        "Google served a consent/CAPTCHA page to the browser "
                        "fetch; falling back for this search")
                    continue
                html_by_url[url] = html
        finally:
            browser.close()
    return html_by_url, warnings
