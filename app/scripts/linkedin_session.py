"""One-time LinkedIn session setup using a `li_at` cookie.

LinkedIn blocks headless logins from data-center IPs with a CAPTCHA/checkpoint.
To avoid that, log into LinkedIn in your own browser, copy the value of the
`li_at` cookie (DevTools -> Application -> Cookies -> https://www.linkedin.com),
and run this script. It loads the cookie, verifies the session against the
feed, and saves a Playwright storage_state to app/data/linkedin_state.json so
the search/apply tasks reuse it and never hit the login flow.

Usage:
    LINKEDIN_LI_AT="<cookie-value>" python scripts/linkedin_session.py
    # or
    python scripts/linkedin_session.py "<cookie-value>"
"""
import os
import sys

# Make `tasks` / `utils` importable when run from the app/ directory.
sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(__file__), "..")))

from playwright.sync_api import sync_playwright

from tasks.linkedin import session as li_session


def main() -> None:
    li_at = (sys.argv[1] if len(sys.argv) > 1 else os.getenv("LINKEDIN_LI_AT", "")).strip()
    if not li_at:
        print(
            "Provide the li_at cookie via the LINKEDIN_LI_AT env var or as the first argument.",
            file=sys.stderr,
        )
        sys.exit(1)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        ctx = browser.new_context(**li_session._CONTEXT_OPTS)
        ctx.add_cookies([{"name": "li_at", "value": li_at, "url": "https://www.linkedin.com"}])
        page = ctx.new_page()

        if li_session.verify_logged_in(page):
            path = li_session.save_state(ctx)
            print(f"Session verified and saved to {path}")
            browser.close()
        else:
            shot = li_session.save_challenge_screenshot(page)
            url = page.url
            browser.close()
            print(
                f"Cookie did NOT authenticate (landed on {url}). Screenshot: {shot}",
                file=sys.stderr,
            )
            sys.exit(2)


if __name__ == "__main__":
    main()
