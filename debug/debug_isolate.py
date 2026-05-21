"""
Isolates whether the failure is headless mode OR missing localStorage from cookie injection.
Run: python debug_isolate.py
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from mad_scraper import auth
from mad_scraper.config import LOGIN_EMAIL, LOGIN_PASSWORD, COOKIES_PATH

load_dotenv()

LESSON_URL = "https://mentoriaamericandr.astronmembers.com/curso/mentoria-american-dream/125393/703533"
BASE_URL = "https://mentoriaamericandr.astronmembers.com"

print("Logging in (non-headless auth browser)...")
cookies = auth.login(LOGIN_EMAIL, LOGIN_PASSWORD, COOKIES_PATH)
print("Login OK\n")

# Test: NON-headless + cookie injection (no browser login)
# If this WORKS  → headless is the cause
# If this FAILS  → missing localStorage/session state is the cause
print("=== Non-headless + cookie injection (no browser login) ===")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    ctx = browser.new_context()
    ctx.add_cookies(cookies)
    page = ctx.new_page()

    page.goto(LESSON_URL)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    local_storage = page.evaluate("() => Object.fromEntries(Object.entries(localStorage))")
    print(f"localStorage keys: {list(local_storage.keys())}")

    soup = BeautifulSoup(page.content(), "html.parser")
    panel = soup.select_one(".aba-anexos")
    links = soup.select("a.box-anexo-action-download")
    print(f"div.aba-anexos present: {panel is not None}")
    print(f"a.box-anexo-action-download count: {len(links)}")

    browser.close()
