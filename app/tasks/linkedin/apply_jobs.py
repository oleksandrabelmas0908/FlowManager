import os
import random
import time

from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

from utils.celery_app import celery_app

_CV_PATH = os.getenv(
    "LINKEDIN_CV_PATH",
    "/root/.claude/uploads/17ea3812-999f-4df1-af67-65ae328c28e6/daf5ebe5-Oleksandr_Abelmas_be.pdf",
)
_PHONE = "+48791846412"


def _login(page) -> None:
    email = os.environ["LINKEDIN_EMAIL"]
    password = os.environ["LINKEDIN_PASSWORD"]
    page.goto("https://www.linkedin.com/login", timeout=30000)
    page.wait_for_selector("input[type='email'], #username", timeout=15000)
    email_sel = "input[type='email']" if page.query_selector("input[type='email']") else "#username"
    pwd_sel = "input[type='password']" if page.query_selector("input[type='password']") else "#password"
    page.fill(email_sel, email)
    page.fill(pwd_sel, password)
    page.click('button[type="submit"]')
    page.wait_for_url("**/feed/**", timeout=25000)


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
            ctx = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
                ignore_https_errors=True,
            )
            page = ctx.new_page()
            _login(page)

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
