import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from .config import LOGIN_URL, HEADLESS

POST_LOGIN_FRAGMENT = "/dashboard"


def login(email: str, password: str, cookies_path: Path) -> list[dict]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        try:
            page = browser.new_page()
            page.goto(LOGIN_URL)
            page.wait_for_load_state("networkidle")
            page.fill("input[type='email']", email)
            page.fill("input[type='password']", password)
            page.click("button[type='submit']")
            page.wait_for_url(f"**{POST_LOGIN_FRAGMENT}**", timeout=20000)
            cookies = page.context.cookies()
        finally:
            browser.close()

    cookies_path.write_text(json.dumps(cookies, indent=2), encoding="utf-8")
    cookies_path.chmod(0o600)
    return cookies


def load_cookies(cookies_path: Path) -> list[dict]:
    if not cookies_path.exists():
        raise FileNotFoundError(f"Cookies file not found: {cookies_path}")
    return json.loads(cookies_path.read_text(encoding="utf-8"))


def cookies_to_netscape(cookies: list[dict]) -> str:
    lines = ["# Netscape HTTP Cookie File"]
    for c in cookies:
        domain = c.get("domain", "")
        include_sub = "TRUE" if domain.startswith(".") else "FALSE"
        secure = "TRUE" if c.get("secure", False) else "FALSE"
        expires_raw = c.get("expires", 0)
        expires = max(0, int(expires_raw)) if expires_raw is not None else 0
        lines.append(
            f"{domain}\t{include_sub}\t{c.get('path', '/')}\t{secure}"
            f"\t{expires}\t{c.get('name', '')}\t{c.get('value', '')}"
        )
    return "\n".join(lines)
