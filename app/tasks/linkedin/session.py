"""Shared LinkedIn authentication for the job-application tasks.

Authentication priority (no interactive CAPTCHA in this headless environment):
  1. Saved Playwright storage_state at app/data/linkedin_state.json (from a
     prior successful run — set up once via scripts/linkedin_session.py).
  2. LINKEDIN_LI_AT cookie env var (the `li_at` session cookie copied from a
     browser where the user is already logged in).
  3. Credential login (LINKEDIN_EMAIL / LINKEDIN_PASSWORD) as a last resort.

If a security checkpoint / CAPTCHA blocks authentication, a screenshot is
written to app/data/linkedin_challenge.png and LinkedInChallenge is raised so
the caller can surface it to the user.
"""
import os

_DATA_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
_STATE_PATH = os.path.join(_DATA_DIR, "linkedin_state.json")
_CHALLENGE_SHOT = os.path.join(_DATA_DIR, "linkedin_challenge.png")

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

_CONTEXT_OPTS = dict(
    user_agent=UA,
    viewport={"width": 1280, "height": 800},
    ignore_https_errors=True,
)


class LinkedInChallenge(Exception):
    """A LinkedIn checkpoint/CAPTCHA is blocking automated access."""

    def __init__(self, url: str, screenshot_path: str):
        self.url = url
        self.screenshot_path = screenshot_path
        super().__init__(f"LinkedIn security challenge at {url} (screenshot: {screenshot_path})")


def has_saved_state() -> bool:
    return os.path.exists(_STATE_PATH)


def is_challenge(page) -> bool:
    url = (page.url or "").lower()
    if "/checkpoint/" in url or "/authwall" in url or "/challenge" in url:
        return True
    return bool(
        page.query_selector(
            "iframe[src*='captcha'], #captcha-internal, .challenge-dialog, [data-test-id='captcha']"
        )
    )


def save_challenge_screenshot(page) -> str:
    os.makedirs(_DATA_DIR, exist_ok=True)
    try:
        page.screenshot(path=_CHALLENGE_SHOT)
    except Exception:
        pass
    return _CHALLENGE_SHOT


def verify_logged_in(page) -> bool:
    """Navigate to the feed and confirm we are authenticated (not bounced to login/checkpoint)."""
    page.goto("https://www.linkedin.com/feed/", timeout=30000)
    url = (page.url or "").lower()
    return "/feed" in url and not is_challenge(page)


def save_state(ctx) -> str:
    """Persist the authenticated session so future runs skip login + challenges."""
    os.makedirs(_DATA_DIR, exist_ok=True)
    ctx.storage_state(path=_STATE_PATH)
    return _STATE_PATH


def _credential_login(page, ctx) -> None:
    email = os.environ["LINKEDIN_EMAIL"]
    password = os.environ["LINKEDIN_PASSWORD"]
    page.goto("https://www.linkedin.com/login", timeout=30000)
    page.wait_for_selector("input[type='email'], #username", timeout=15000)
    email_sel = "input[type='email']" if page.query_selector("input[type='email']") else "#username"
    pwd_sel = "input[type='password']" if page.query_selector("input[type='password']") else "#password"
    page.fill(email_sel, email)
    page.fill(pwd_sel, password)
    page.click('button[type="submit"]')
    try:
        page.wait_for_url("**/feed/**", timeout=25000)
    except Exception:
        if is_challenge(page):
            raise LinkedInChallenge(page.url, save_challenge_screenshot(page))
        raise


def new_authenticated_context(browser):
    """Return a browser context authenticated against LinkedIn.

    Raises LinkedInChallenge if a checkpoint/CAPTCHA blocks credential login.
    """
    if has_saved_state():
        return browser.new_context(storage_state=_STATE_PATH, **_CONTEXT_OPTS)

    ctx = browser.new_context(**_CONTEXT_OPTS)

    li_at = os.getenv("LINKEDIN_LI_AT", "").strip()
    if li_at:
        ctx.add_cookies([{"name": "li_at", "value": li_at, "url": "https://www.linkedin.com"}])
        return ctx

    page = ctx.new_page()
    _credential_login(page, ctx)
    return ctx
