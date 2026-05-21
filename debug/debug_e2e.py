"""
End-to-end diagnostic: extract_with_page + download_attachment for lesson 703533.
Run: python debug_e2e.py
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from pathlib import Path

from mad_scraper import auth, extractor, downloader
from mad_scraper.models import Lesson
from mad_scraper.config import LOGIN_EMAIL, LOGIN_PASSWORD, COOKIES_PATH, HEADLESS

load_dotenv()

LESSON_URL = "https://mentoriaamericandr.astronmembers.com/curso/mentoria-american-dream/125393/703533"

lesson = Lesson(
    url=LESSON_URL, titulo="Test 703533",
    modulo="Test", modulo_index=1, aula_index=1,
)

print(f"HEADLESS={HEADLESS}")
print("Logging in...")
cookies = auth.login(LOGIN_EMAIL, LOGIN_PASSWORD, COOKIES_PATH)
print("Login OK")

with sync_playwright() as p:
    _args = ["--window-position=-32000,-32000"] if HEADLESS else []
    browser = p.chromium.launch(headless=False, args=_args)
    ctx = browser.new_context()
    ctx.add_cookies(cookies)
    page = ctx.new_page()

    print("Calling extract_with_page (this is the real extractor)...")
    content = extractor.extract_with_page(lesson, page)

    print(f"\nAttachments found: {len(content.anexos)}")
    for a in content.anexos:
        print(f"  nome={a.nome!r}")
        print(f"  url={a.url!r}")
        print(f"  filename={a.filename!r}")

    if not content.anexos:
        print("\n*** FINDING FAILED — getting raw HTML to inspect ***")
        from bs4 import BeautifulSoup
        page.goto(LESSON_URL)
        page.wait_for_load_state("networkidle")
        soup = BeautifulSoup(page.content(), "html.parser")
        panel = soup.select_one(".aba-anexos")
        print(f"div.aba-anexos present: {panel is not None}")
        links = soup.select("a.box-anexo-action-download")
        print(f"a.box-anexo-action-download count: {len(links)}")
    else:
        att = content.anexos[0]
        print(f"\nTesting download of: {att.filename}")
        dest = Path("test-download-e2e")

        # Use Playwright BrowserContext — NOT plain requests.
        # The server validates full browser session state (headers, origin,
        # CSRF) so plain requests with just cookies get 403.
        ok = downloader.download_attachment_with_context(
            att.url, dest, ctx, filename=att.filename
        )
        print(f"Download result: {ok}")
        if ok:
            f = dest / att.filename
            size = f.stat().st_size
            print(f"File size: {size:,} bytes")
            if size < 100:
                print(f"WARNING: file too small, likely a redirect/login page. Content: {f.read_bytes()}")
            else:
                print("SUCCESS — attachment downloaded correctly!")
        else:
            # Diagnose: try with Playwright page navigation as fallback
            print("DOWNLOAD FAILED via context.request — trying page-based download...")
            try:
                with page.expect_download(timeout=15000) as dl_info:
                    page.goto(att.url)
                download = dl_info.value
                save_path = dest / att.filename
                dest.mkdir(parents=True, exist_ok=True)
                download.save_as(str(save_path))
                size = save_path.stat().st_size
                print(f"Page-based download SUCCESS! Size: {size:,} bytes")
            except Exception as e:
                print(f"Page-based download also failed: {e}")
                print("\nDiagnosing with raw context.request...")
                try:
                    resp = ctx.request.get(att.url, headers={
                        "Referer": "https://mentoriaamericandr.astronmembers.com"
                    })
                    print(f"  Status: {resp.status}")
                    print(f"  Status text: {resp.status_text}")
                    print(f"  Headers: {dict(resp.headers)}")
                    body = resp.body()
                    print(f"  Body size: {len(body)} bytes")
                    if len(body) < 500:
                        print(f"  Body text: {body[:500]}")
                except Exception as e2:
                    print(f"  Context request also failed: {e2}")

    browser.close()
