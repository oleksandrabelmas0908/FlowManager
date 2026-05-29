import os
import random
import time

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

from utils.celery_app import celery_app
from .session import (
    LinkedInChallenge,
    is_challenge,
    new_authenticated_context,
    save_challenge_screenshot,
    save_state,
)

_CV_PATH = os.getenv(
    "LINKEDIN_CV_PATH",
    "/root/.claude/uploads/17ea3812-999f-4df1-af67-65ae328c28e6/daf5ebe5-Oleksandr_Abelmas_be.pdf",
)
_PHONE = "+48791846412"


def _fill_phone_if_needed(page) -> None:
    try:
        phone_input = page.query_selector("input[id*='phoneNumber'], input[name*='phoneNumber']")
        if phone_input:
            current = phone_input.input_value()
            if not current.strip():
                phone_input.fill(_PHONE)
    except Exception:
        pass


def _upload_cv_if_needed(page) -> None:
    try:
        upload_input = page.query_selector("input[type='file']")
        if upload_input and os.path.exists(_CV_PATH):
            upload_input.set_input_files(_CV_PATH)
            time.sleep(1.5)
    except Exception:
        pass


def _answer_extra_questions(page) -> None:
    """Fill required text/select fields with safe defaults; skip optional ones."""
    try:
        # Fill empty required text inputs with a safe answer
        inputs = page.query_selector_all(
            "div.jobs-easy-apply-form-section__grouping input[required], "
            "div.jobs-easy-apply-form-section__grouping textarea[required]"
        )
        for inp in inputs:
            if not inp.input_value().strip():
                inp.fill("Yes")
    except Exception:
        pass

    try:
        # Pick first option in any required selects that are unset
        selects = page.query_selector_all(
            "div.jobs-easy-apply-form-section__grouping select[required]"
        )
        for sel in selects:
            options = sel.query_selector_all("option")
            if options and len(options) > 1:
                sel.select_option(index=1)
    except Exception:
        pass


def _apply_to_job(page, job: dict) -> str:
    """
    Returns: 'applied', 'skipped', or 'failed'.
    """
    try:
        page.goto(job["url"], timeout=30000)
        time.sleep(random.uniform(2, 4))

        # Find and click Easy Apply button
        easy_apply_btn = page.query_selector(
            "button.jobs-apply-button[aria-label*='Easy Apply'], "
            "button[aria-label*='Easy Apply']"
        )
        if not easy_apply_btn:
            return "skipped"

        easy_apply_btn.click()
        time.sleep(2)

        # Step through the modal
        for _ in range(10):
            _fill_phone_if_needed(page)
            _upload_cv_if_needed(page)
            _answer_extra_questions(page)

            # Check for Submit button (final step)
            submit_btn = page.query_selector(
                "button[aria-label='Submit application'], "
                "footer button.artdeco-button--primary"
            )
            if submit_btn and "submit" in (submit_btn.get_attribute("aria-label") or "").lower():
                submit_btn.click()
                time.sleep(2)
                return "applied"

            # Check for Next / Review button
            next_btn = page.query_selector(
                "button[aria-label='Continue to next step'], "
                "button[aria-label='Review your application'], "
                "footer button.artdeco-button--primary"
            )
            if next_btn:
                next_btn.click()
                time.sleep(1.5)
                continue

            # Modal may have closed (already applied or error)
            modal = page.query_selector("div.jobs-easy-apply-modal")
            if not modal:
                break

        # If we reach here, check if application was submitted anyway
        return "failed"

    except PWTimeoutError:
        return "failed"
    except Exception:
        return "failed"


@celery_app.task(name="linkedin_apply_jobs")
def apply_linkedin_jobs(context: dict) -> dict:
    """Open each filtered job and submit via LinkedIn Easy Apply."""
    try:
        previous = context.get("previous_results", [])
        filter_output = next(
            (r["output"] for r in previous if r["task_name"] == "linkedin_filter_jobs"),
            None,
        )
        if not filter_output:
            return {"outcome": "failure", "data": {"error": "No output from linkedin_filter_jobs"}}

        filtered_jobs = filter_output.get("filtered_jobs", [])
        if not filtered_jobs:
            return {
                "outcome": "success",
                "data": {"applied": [], "failed": [], "total_applied": 0, "message": "No matching jobs found"},
            }

        applied = []
        failed = []

        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
            try:
                ctx = new_authenticated_context(browser)
            except LinkedInChallenge as ch:
                browser.close()
                return {
                    "outcome": "failure",
                    "data": {
                        "error": "LinkedIn security challenge — provide a fresh li_at cookie or saved session",
                        "challenge_url": ch.url,
                        "screenshot": ch.screenshot_path,
                    },
                }

            page = ctx.new_page()

            page.goto("https://www.linkedin.com/feed/", timeout=30000)
            if is_challenge(page) or "/feed" not in (page.url or ""):
                shot = save_challenge_screenshot(page)
                challenge_url = page.url
                browser.close()
                return {
                    "outcome": "failure",
                    "data": {
                        "error": "Not authenticated — session expired or cookie invalid",
                        "challenge_url": challenge_url,
                        "screenshot": shot,
                    },
                }

            for job in filtered_jobs:
                result = _apply_to_job(page, job)
                entry = {
                    "job_id": job["job_id"],
                    "title": job["title"],
                    "company": job["company"],
                    "url": job["url"],
                    "result": result,
                }
                if result == "applied":
                    applied.append(entry)
                else:
                    failed.append(entry)

                time.sleep(random.uniform(3, 7))

            # Refresh the persisted session so later runs keep skipping login.
            try:
                save_state(ctx)
            except Exception:
                pass

            browser.close()

        return {
            "outcome": "success",
            "data": {
                "applied": applied,
                "failed": failed,
                "total_applied": len(applied),
            },
        }
    except Exception as e:
        return {"outcome": "failure", "data": {"error": str(e)}}
