"""
core/applier.py
Auto-apply automation module. Uses Playwright (headless browser) to automate
application submission for job boards that support easy-apply / quick-apply.

Supported platforms:
  - LinkedIn Easy Apply (via Playwright)
  - Indeed Quick Apply (via Playwright)
  - Direct URL form detection & submission

IMPORTANT: This only works with jobs that have "Easy Apply" / "Quick Apply"
features. It does NOT bypass login walls — you must provide credentials in .env.
All automation is done in a way that respects rate limits.

Setup:
  pip install playwright
  playwright install chromium
"""

import os
import time
import logging
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

from core import tracker

logger = logging.getLogger(__name__)


@dataclass
class ApplyConfig:
    """Configuration for auto-apply. All loaded from env / session."""
    resume_path: str = ""
    cover_letter_text: str = ""
    # LinkedIn
    linkedin_email: str = field(default_factory=lambda: os.getenv("LINKEDIN_EMAIL", ""))
    linkedin_password: str = field(default_factory=lambda: os.getenv("LINKEDIN_PASSWORD", ""))
    # Indeed
    indeed_email: str = field(default_factory=lambda: os.getenv("INDEED_EMAIL", ""))
    indeed_password: str = field(default_factory=lambda: os.getenv("INDEED_PASSWORD", ""))
    # Behavior
    headless: bool = True
    slow_mo: int = 500   # ms between actions (be polite to servers)
    timeout: int = 30000  # ms


@dataclass
class ApplyResult:
    job_url: str
    company: str
    role: str
    success: bool
    message: str
    platform: str = ""


def _is_playwright_available() -> bool:
    try:
        import playwright  # noqa
        return True
    except ImportError:
        return False


def _detect_platform(url: str) -> str:
    """Detect which job board the URL belongs to."""
    url_lower = url.lower()
    if "linkedin.com" in url_lower:
        return "linkedin"
    if "indeed.com" in url_lower:
        return "indeed"
    if "greenhouse.io" in url_lower:
        return "greenhouse"
    if "lever.co" in url_lower:
        return "lever"
    if "workday.com" in url_lower or "myworkdayjobs.com" in url_lower:
        return "workday"
    return "unknown"


def apply_to_job(
    job_url: str,
    company: str,
    role: str,
    config: ApplyConfig,
    progress_callback=None,
) -> ApplyResult:
    """
    Attempt to auto-apply to a single job.
    Returns ApplyResult with success/failure info.
    progress_callback(message: str) is called with status updates.
    """
    if not _is_playwright_available():
        return ApplyResult(
            job_url=job_url, company=company, role=role,
            success=False,
            message="Playwright is not installed. Run: pip install playwright && playwright install chromium",
            platform="none"
        )

    platform = _detect_platform(job_url)

    def log(msg):
        logger.info(msg)
        if progress_callback:
            progress_callback(msg)

    log(f"🔍 Detected platform: {platform} for {job_url}")

    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=config.headless,
                slow_mo=config.slow_mo,
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1366, "height": 768},
            )
            page = context.new_page()

            try:
                if platform == "linkedin":
                    result = _apply_linkedin(page, job_url, company, role, config, log)
                elif platform == "indeed":
                    result = _apply_indeed(page, job_url, company, role, config, log)
                elif platform in ("greenhouse", "lever"):
                    result = _apply_ats_board(page, job_url, company, role, config, log, platform)
                else:
                    result = _apply_generic(page, job_url, company, role, config, log)

                if result.success:
                    # Update tracker status to "Applied"
                    apps = tracker.list_applications()
                    for app in apps:
                        if app["url"] == job_url:
                            tracker.update_status(app["id"], "Applied")
                            break

                return result

            except PlaywrightTimeout as e:
                return ApplyResult(
                    job_url=job_url, company=company, role=role,
                    success=False,
                    message=f"Timed out during application: {str(e)[:200]}",
                    platform=platform,
                )
            finally:
                browser.close()

    except Exception as e:
        return ApplyResult(
            job_url=job_url, company=company, role=role,
            success=False,
            message=f"Error during automation: {str(e)[:300]}",
            platform=platform,
        )


def _apply_linkedin(page, url: str, company: str, role: str, config: ApplyConfig, log) -> ApplyResult:
    """LinkedIn Easy Apply flow."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeout

    log("🔐 Logging into LinkedIn...")

    # Login
    page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
    page.fill("#username", config.linkedin_email)
    page.fill("#password", config.linkedin_password)
    page.click("[data-litms-control-urn='login-submit']")

    try:
        page.wait_for_url("**/feed/**", timeout=15000)
        log("✅ LinkedIn login successful")
    except PlaywrightTimeout:
        # Check if we got a captcha / 2FA page
        if "checkpoint" in page.url or "challenge" in page.url:
            return ApplyResult(
                job_url=url, company=company, role=role,
                success=False,
                message="LinkedIn requires CAPTCHA or 2FA verification. Please log in manually first.",
                platform="linkedin",
            )
        # May already be logged in
        log("⚠️ Login redirect uncertain, continuing...")

    log(f"📋 Navigating to job listing: {url}")
    page.goto(url, wait_until="domcontentloaded")
    time.sleep(2)

    # Look for Easy Apply button
    easy_apply_btn = page.locator("button:has-text('Easy Apply')").first
    if not easy_apply_btn.is_visible():
        return ApplyResult(
            job_url=url, company=company, role=role,
            success=False,
            message="No 'Easy Apply' button found. This job requires external application.",
            platform="linkedin",
        )

    log("🖱️ Clicking Easy Apply...")
    easy_apply_btn.click()
    time.sleep(1)

    # Handle the Easy Apply modal - fill basic info & step through
    steps_completed = 0
    max_steps = 10

    while steps_completed < max_steps:
        # Check for Next/Review/Submit button
        next_btn = page.locator("button:has-text('Next')").first
        review_btn = page.locator("button:has-text('Review')").first
        submit_btn = page.locator("button:has-text('Submit application')").first

        if submit_btn.is_visible():
            log("📤 Submitting application...")
            submit_btn.click()
            time.sleep(2)
            return ApplyResult(
                job_url=url, company=company, role=role,
                success=True,
                message="✅ Successfully submitted via LinkedIn Easy Apply!",
                platform="linkedin",
            )

        if review_btn.is_visible():
            log("📋 Reviewing application...")
            review_btn.click()
            time.sleep(1)
            steps_completed += 1
            continue

        if next_btn.is_visible():
            # Try to fill any required fields before clicking next
            _fill_linkedin_form_fields(page, config)
            log(f"➡️ Moving to step {steps_completed + 2}...")
            next_btn.click()
            time.sleep(1.5)
            steps_completed += 1
        else:
            # No navigation buttons found
            break

    return ApplyResult(
        job_url=url, company=company, role=role,
        success=False,
        message="Could not complete LinkedIn Easy Apply — application may require manual fields.",
        platform="linkedin",
    )


def _fill_linkedin_form_fields(page, config: ApplyConfig):
    """Fill common LinkedIn Easy Apply form fields."""
    try:
        # Phone number
        phone_field = page.locator("input[id*='phoneNumber']").first
        if phone_field.is_visible() and not phone_field.input_value():
            phone = os.getenv("PHONE_NUMBER", "")
            if phone:
                phone_field.fill(phone)

        # Upload resume if file input exists
        if config.resume_path and Path(config.resume_path).exists():
            resume_input = page.locator("input[type='file']").first
            if resume_input.is_visible():
                resume_input.set_input_files(config.resume_path)

        # Cover letter / additional info textareas
        if config.cover_letter_text:
            textareas = page.locator("textarea").all()
            for ta in textareas:
                if ta.is_visible() and not ta.input_value():
                    placeholder = ta.get_attribute("placeholder") or ""
                    if any(kw in placeholder.lower() for kw in ["cover", "additional", "message"]):
                        ta.fill(config.cover_letter_text[:2000])
                        break

        # Handle Yes/No radio buttons (default to "Yes" for generic questions)
        radio_yes = page.locator("label:has-text('Yes')").first
        if radio_yes.is_visible():
            radio_yes.click()

    except Exception:
        pass  # Best-effort field filling


def _apply_indeed(page, url: str, company: str, role: str, config: ApplyConfig, log) -> ApplyResult:
    """Indeed Quick Apply flow."""
    from playwright.sync_api import TimeoutError as PlaywrightTimeout

    log("🔐 Logging into Indeed...")
    page.goto("https://secure.indeed.com/auth", wait_until="domcontentloaded")

    try:
        page.fill("input[type='email']", config.indeed_email)
        page.click("button[type='submit']")
        time.sleep(1)
        page.fill("input[type='password']", config.indeed_password)
        page.click("button[type='submit']")
        page.wait_for_url("**/*/", timeout=15000)
        log("✅ Indeed login successful")
    except Exception as e:
        return ApplyResult(
            job_url=url, company=company, role=role,
            success=False,
            message=f"Indeed login failed: {str(e)[:200]}",
            platform="indeed",
        )

    log(f"📋 Navigating to job: {url}")
    page.goto(url, wait_until="domcontentloaded")
    time.sleep(2)

    # Look for Indeed Apply / Quick Apply
    apply_btn = page.locator("button:has-text('Apply now'), button:has-text('Quick Apply')").first
    if not apply_btn.is_visible():
        return ApplyResult(
            job_url=url, company=company, role=role,
            success=False,
            message="No Quick Apply button found on Indeed listing.",
            platform="indeed",
        )

    apply_btn.click()
    time.sleep(2)

    # Step through the application
    for _ in range(8):
        # Upload resume if prompted
        file_inputs = page.locator("input[type='file']").all()
        for fi in file_inputs:
            if fi.is_visible() and config.resume_path and Path(config.resume_path).exists():
                fi.set_input_files(config.resume_path)
                time.sleep(1)

        # Continue / Submit
        cont_btn = page.locator("button:has-text('Continue'), button:has-text('Submit')").first
        if cont_btn.is_visible():
            if "Submit" in (cont_btn.text_content() or ""):
                cont_btn.click()
                time.sleep(2)
                return ApplyResult(
                    job_url=url, company=company, role=role,
                    success=True,
                    message="✅ Successfully submitted via Indeed Quick Apply!",
                    platform="indeed",
                )
            cont_btn.click()
            time.sleep(1.5)

    return ApplyResult(
        job_url=url, company=company, role=role,
        success=False,
        message="Could not complete Indeed application — may require manual fields.",
        platform="indeed",
    )


def _apply_ats_board(page, url: str, company: str, role: str, config: ApplyConfig, log, platform: str) -> ApplyResult:
    """Generic Greenhouse / Lever ATS application."""
    log(f"📋 Opening {platform} application page...")
    page.goto(url, wait_until="domcontentloaded")
    time.sleep(2)

    # Fill basic fields
    _fill_generic_form(page, config)

    # Submit
    submit = page.locator("input[type='submit'], button[type='submit']").first
    if submit.is_visible():
        submit.click()
        time.sleep(2)
        return ApplyResult(
            job_url=url, company=company, role=role,
            success=True,
            message=f"✅ Application submitted via {platform.title()}!",
            platform=platform,
        )

    return ApplyResult(
        job_url=url, company=company, role=role,
        success=False,
        message=f"Could not find submit button on {platform} form.",
        platform=platform,
    )


def _apply_generic(page, url: str, company: str, role: str, config: ApplyConfig, log) -> ApplyResult:
    """Best-effort generic application form filler."""
    log("📋 Opening job application URL (generic handler)...")
    page.goto(url, wait_until="domcontentloaded")
    time.sleep(2)

    _fill_generic_form(page, config)

    submit = page.locator("input[type='submit'], button[type='submit'], button:has-text('Apply')").first
    if submit.is_visible():
        submit.click()
        time.sleep(2)
        return ApplyResult(
            job_url=url, company=company, role=role,
            success=True,
            message="✅ Application submitted (generic form)!",
            platform="generic",
        )

    return ApplyResult(
        job_url=url, company=company, role=role,
        success=False,
        message="Could not auto-apply — this job requires manual application. The listing has been saved to your tracker.",
        platform="generic",
    )


def _fill_generic_form(page, config: ApplyConfig):
    """Fill common application form fields by common field names/types."""
    try:
        # Name
        first_name = os.getenv("FIRST_NAME", "")
        last_name = os.getenv("LAST_NAME", "")
        email = os.getenv("APPLY_EMAIL", config.linkedin_email or config.indeed_email)
        phone = os.getenv("PHONE_NUMBER", "")

        for selector, value in [
            ("input[name*='first'], input[id*='first'], input[placeholder*='First']", first_name),
            ("input[name*='last'], input[id*='last'], input[placeholder*='Last']", last_name),
            ("input[type='email'], input[name*='email']", email),
            ("input[type='tel'], input[name*='phone']", phone),
        ]:
            if value:
                try:
                    field = page.locator(selector).first
                    if field.is_visible() and not field.input_value():
                        field.fill(value)
                except Exception:
                    pass

        # Resume upload
        if config.resume_path and Path(config.resume_path).exists():
            try:
                file_input = page.locator("input[type='file']").first
                if file_input.is_visible():
                    file_input.set_input_files(config.resume_path)
                    time.sleep(0.5)
            except Exception:
                pass

        # Cover letter textarea
        if config.cover_letter_text:
            try:
                textarea = page.locator("textarea[name*='cover'], textarea[id*='cover'], textarea[placeholder*='cover']").first
                if textarea.is_visible():
                    textarea.fill(config.cover_letter_text[:2000])
            except Exception:
                pass

    except Exception:
        pass


def batch_apply(
    jobs: list[dict],
    config: ApplyConfig,
    progress_callback=None,
    delay_between: float = 3.0,
) -> list[ApplyResult]:
    """
    Apply to multiple jobs sequentially.
    jobs: list of dicts with keys: url, company, role
    delay_between: seconds to wait between applications (be polite!)
    """
    results = []
    for i, job in enumerate(jobs):
        url = job.get("url", "")
        company = job.get("company", "Unknown")
        role = job.get("role") or job.get("title", "Unknown")

        if progress_callback:
            progress_callback(f"Applying to job {i+1}/{len(jobs)}: {role} at {company}")

        result = apply_to_job(url, company, role, config, progress_callback)
        results.append(result)

        if i < len(jobs) - 1:
            time.sleep(delay_between)

    return results
