"""
Tests whether logging in through the headless browser (not cookie injection)
fixes the aba-anexos rendering issue.
Run: python debug_headless_login.py
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

load_dotenv()
EMAIL = os.getenv("LOGIN_EMAIL", "")
PASSWORD = os.getenv("LOGIN_PASSWORD", "")

LESSON_URL = "https://mentoriaamericandr.astronmembers.com/curso/mentoria-american-dream/125393/703533"
LOGIN_URL = "https://mentoriaamericandr.astronmembers.com/entrar"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)  # headless, but login through browser
    ctx = browser.new_context()
    page = ctx.new_page()

    print("Logging in via headless browser (no cookie injection)...")
    page.goto(LOGIN_URL)
    page.wait_for_load_state("networkidle")
    page.fill("input[type='email']", EMAIL)
    page.fill("input[type='password']", PASSWORD)
    page.click("button[type='submit']")
    page.wait_for_url("**/dashboard**", timeout=20000)
    print("Login OK")

    # Dump localStorage to see what's there
    local_storage = page.evaluate("() => Object.entries(localStorage)")
    print(f"localStorage keys after login: {[k for k, v in local_storage]}")

    print(f"\nNavigating to lesson 703533...")
    page.goto(LESSON_URL)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)

    soup = BeautifulSoup(page.content(), "html.parser")
    panel = soup.select_one(".aba-anexos")
    links = soup.select("a.box-anexo-action-download")
    print(f"div.aba-anexos present: {panel is not None}")
    print(f"a.box-anexo-action-download count: {len(links)}")
    if links:
        print(f"  href={links[0].get('href')!r}")
        print(f"  download={links[0].get('download')!r}")

    browser.close()
