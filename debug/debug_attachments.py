"""
Diagnostic: capture raw HTML from lesson 703533 (has attachments).
Run: python debug_attachments.py
Saves: debug_before_click.html, debug_after_click.html, debug_report.txt
"""
import os, sys
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
EMAIL = os.getenv("LOGIN_EMAIL", "")
PASSWORD = os.getenv("LOGIN_PASSWORD", "")
LESSON_URL = "https://mentoriaamericandr.astronmembers.com/curso/mentoria-american-dream/125393/703533"
LOGIN_URL = "https://mentoriaamericandr.astronmembers.com/login"

def save(path, html):
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved {path} ({len(html)} bytes)")

def report(html, label):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    lines = [f"\n=== {label} ==="]

    panel = soup.select_one(".aba-anexos")
    lines.append(f"div.aba-anexos present: {panel is not None}")
    if panel:
        lines.append(f"  inner HTML (500): {str(panel)[:500]}")

    btn = soup.select_one("button[data-aba='anexos']")
    lines.append(f"button[data-aba=anexos] present: {btn is not None}")
    if btn:
        lines.append(f"  button HTML: {str(btn)[:200]}")

    dl_links = soup.select("a.box-anexo-action-download")
    lines.append(f"a.box-anexo-action-download count: {len(dl_links)}")
    for i, a in enumerate(dl_links):
        lines.append(f"  [{i}] href={a.get('href','')!r}  download={a.get('download','')!r}")

    tab_buttons = soup.select("button.aba")
    lines.append(f"All button.aba tabs: {[b.get('data-aba') for b in tab_buttons]}")

    abas = soup.select("div.curso-aba")
    lines.append(f"div.curso-aba panels: {[a.get('class') for a in abas]}")

    return "\n".join(lines)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    ctx = browser.new_context()
    page = ctx.new_page()

    print("Logging in...")
    page.goto(LOGIN_URL)
    page.wait_for_load_state("networkidle")
    page.fill("input[type='email']", EMAIL)
    page.fill("input[type='password']", PASSWORD)
    page.click("button[type='submit']")
    page.wait_for_url("**/dashboard**", timeout=15000)
    print("Login OK")

    print(f"Navigating to lesson...")
    page.goto(LESSON_URL)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2000)

    html_before = page.content()
    save("debug_before_click.html", html_before)
    r1 = report(html_before, "BEFORE clicking Anexos tab")

    # Try clicking the Anexos tab
    print("Checking for Anexos tab button...")
    btn_sel = "button[data-aba='anexos']"
    has_btn = page.locator(btn_sel).count() > 0
    print(f"Anexos tab button found: {has_btn}")

    if has_btn:
        page.click(btn_sel)
        page.wait_for_timeout(3000)
        html_after = page.content()
        save("debug_after_click.html", html_after)
        r2 = report(html_after, "AFTER clicking Anexos tab")
    else:
        r2 = "\n=== AFTER clicking Anexos tab ===\n(tab button not found, skipped)"
        print("No Anexos tab button — lesson may not have attachments or selector is wrong")
        print("Checking all tab buttons on page:")
        for btn in page.locator("button.aba").all():
            print(f"  data-aba={btn.get_attribute('data-aba')!r}  text={btn.inner_text()!r}")

    full_report = r1 + r2
    print(full_report)

    with open("debug_report.txt", "w", encoding="utf-8") as f:
        f.write(full_report)
    print("\nSaved debug_report.txt")

    browser.close()
