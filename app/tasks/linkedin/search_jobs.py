import os
import random
import time

from playwright.sync_api import sync_playwright

from utils.celery_app import celery_app

_SEARCH_QUERIES = [
    "Senior Backend Engineer Python",
    "Python Backend Engineer",
    "Backend Python Developer",
]

_LOCATIONS = ["Poland", "Remote"]

_MAX_JOBS_PER_SEARCH = 15


def _build_search_url(keywords: str, location: str) -> str:
    import urllib.parse
    params = {
        "keywords": keywords,
        "location": location,
        "f_AL": "true",  # Easy Apply filter
        "sortBy": "DD",  # Most recent
    }
    return "https://www.linkedin.com/jobs/search/?" + urllib.parse.urlencode(params)


def _login(page) -> None:
    email = os.environ["LINKEDIN_EMAIL"]
    password = os.environ["LINKEDIN_PASSWORD"]

    page.goto("https://www.linkedin.com/login", timeout=30000)
    page.wait_for_selector("#username", timeout=15000)
    page.fill("#username", email)
    page.fill("#password", password)
    page.click('button[type="submit"]')
    page.wait_for_url("**/feed/**", timeout=20000)


def _scrape_job_cards(page, url: str) -> list[dict]:
    page.goto(url, timeout=30000)
    time.sleep(random.uniform(2, 4))

    jobs = []
    try:
        page.wait_for_selector(".jobs-search__results-list, .scaffold-layout__list", timeout=10000)
    except Exception:
        return jobs

    cards = page.query_selector_all("li.jobs-search-results__list-item, li[data-occludable-job-id]")
    for card in cards[:_MAX_JOBS_PER_SEARCH]:
        try:
            job_id = card.get_attribute("data-occludable-job-id") or card.get_attribute("data-job-id") or ""
            title_el = card.query_selector(".job-card-list__title, .base-search-card__title")
            company_el = card.query_selector(".job-card-container__primary-description, .base-search-card__subtitle")
            location_el = card.query_selector(".job-card-container__metadata-item, .job-search-card__location")
            link_el = card.query_selector("a.job-card-list__title--link, a.base-card__full-link")

            title = title_el.inner_text().strip() if title_el else ""
            company = company_el.inner_text().strip() if company_el else ""
            job_location = location_el.inner_text().strip() if location_el else ""
            href = link_el.get_attribute("href") if link_el else ""

            if not job_id and href:
                import re
                m = re.search(r"/jobs/view/(\d+)", href)
                job_id = m.group(1) if m else href

            if job_id and title:
                jobs.append({
                    "job_id": job_id,
                    "title": title,
                    "company": company,
                    "location": job_location,
                    "url": f"https://www.linkedin.com/jobs/view/{job_id}/" if job_id.isdigit() else href,
                    "easy_apply": True,
                })
        except Exception:
            continue

    return jobs


@celery_app.task(name="linkedin_search_jobs")
def search_linkedin_jobs(context: dict) -> dict:
    """Login to LinkedIn and search for Senior Backend Engineer jobs (Easy Apply)."""
    try:
        all_jobs: dict[str, dict] = {}

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
            )
            page = ctx.new_page()

            _login(page)

            for query in _SEARCH_QUERIES:
                for location in _LOCATIONS:
                    url = _build_search_url(query, location)
                    try:
                        jobs = _scrape_job_cards(page, url)
                        for job in jobs:
                            all_jobs.setdefault(job["job_id"], job)
                        time.sleep(random.uniform(1.5, 3.0))
                    except Exception as e:
                        continue

            browser.close()

        jobs_list = list(all_jobs.values())
        return {
            "outcome": "success",
            "data": {"jobs": jobs_list, "total_found": len(jobs_list)},
        }
    except Exception as e:
        return {"outcome": "failure", "data": {"error": str(e)}}
