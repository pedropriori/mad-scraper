"""
Tests two approaches to get aba-anexos in headless mode.
Run: python debug_fix_candidates.py
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import requests

from mad_scraper import auth
from mad_scraper.config import LOGIN_EMAIL, LOGIN_PASSWORD, COOKIES_PATH

load_dotenv()

LESSON_URL = "https://mentoriaamericandr.astronmembers.com/curso/mentoria-american-dream/125393/703533"
BASE_URL = "https://mentoriaamericandr.astronmembers.com"

print("Logging in...")
cookies = auth.login(LOGIN_EMAIL, LOGIN_PASSWORD, COOKIES_PATH)
print("Login OK\n")

session_cookies = {c["name"]: c["value"] for c in cookies}

# ── Approach A: requests.get (raw server HTML, no JavaScript) ────────────────
print("=== Approach A: requests.get (no JS) ===")
resp = requests.get(LESSON_URL, cookies=session_cookies,
                    headers={"Referer": BASE_URL, "User-Agent": "Mozilla/5.0"},
                    timeout=20)
print(f"HTTP {resp.status_code}  final URL: {resp.url}")
soup_a = BeautifulSoup(resp.text, "html.parser")
panel_a = soup_a.select_one(".aba-anexos")
links_a = soup_a.select("a.box-anexo-action-download")
print(f"div.aba-anexos present: {panel_a is not None}")
print(f"a.box-anexo-action-download count: {len(links_a)}")
if links_a:
    print(f"  href={links_a[0].get('href')!r}  download={links_a[0].get('download')!r}")

print()

# ── Approach B: headless Playwright with anti-detection flags ────────────────
print("=== Approach B: headless Playwright + anti-detection ===")
with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=["--disable-blink-features=AutomationControlled"],
    )
    ctx = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        )
    )
    ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    ctx.add_cookies(cookies)
    page = ctx.new_page()

    page.goto(LESSON_URL)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    soup_b = BeautifulSoup(page.content(), "html.parser")
    panel_b = soup_b.select_one(".aba-anexos")
    links_b = soup_b.select("a.box-anexo-action-download")
    print(f"div.aba-anexos present: {panel_b is not None}")
    print(f"a.box-anexo-action-download count: {len(links_b)}")
    if links_b:
        print(f"  href={links_b[0].get('href')!r}  download={links_b[0].get('download')!r}")

    browser.close()

print("\nDone.")
