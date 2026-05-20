import json
from pathlib import Path
from playwright.sync_api import sync_playwright

from .config import AUTH_HEADLESS, LOGIN_URL

POST_LOGIN_FRAGMENT = "/dashboard"


def login(email: str, password: str, cookies_path: Path) -> list[dict]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=AUTH_HEADLESS)
        page = browser.new_page()
        page.goto(LOGIN_URL)
        page.wait_for_load_state("networkidle")
        page.fill("input[type='email']", email)
        page.fill("input[type='password']", password)
        page.click("button[type='submit']")
        page.wait_for_url(f"**{POST_LOGIN_FRAGMENT}**", timeout=20000)
        cookies = page.context.cookies()
        browser.close()

    cookies_path.write_text(json.dumps(cookies, indent=2), encoding="utf-8")
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
        lines.append(
            f"{domain}\t{include_sub}\t{c.get('path', '/')}\t{secure}"
            f"\t{int(c.get('expires', 0))}\t{c.get('name', '')}\t{c.get('value', '')}"
        )
    return "\n".join(lines)
