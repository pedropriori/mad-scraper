import logging

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from .config import BASE_URL
from .models import Lesson

LESSON_HREF_PATTERN = "mentoria-american-dream"


def get_lessons(course_url: str, cookies: list[dict]) -> list[Lesson]:
    """Navigate to course, then extract full lesson list from sidebar of any lesson page."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        context.add_cookies(cookies)
        page = context.new_page()

        # Navigate to course page
        page.goto(course_url)
        page.wait_for_load_state("networkidle")

        # Click first module header to navigate to a lesson page (where sidebar loads fully)
        try:
            page.click("dl.modulo-container dt", timeout=10000)
            page.wait_for_load_state("networkidle")
        except Exception as e:
            logging.debug("Module click triggered navigation or failed: %s", e)

        # Wait for sidebar with lesson list to load
        try:
            page.wait_for_selector(".videos .accordion.scroll dl", timeout=15000)
        except Exception as e:
            logging.warning("Sidebar selector not found: %s", e)

        html = page.content()
        browser.close()

    return _parse_lessons_html(html, BASE_URL)


def _parse_lessons_html(html: str, base_url: str) -> list[Lesson]:
    """Parse lesson list from the sidebar HTML of a lesson page."""
    soup = BeautifulSoup(html, "html.parser")

    # Find the accordion inside .videos sidebar
    accordion = soup.select_one(".accordion.scroll") or soup.select_one(".accordion")
    if accordion is None:
        return []

    lessons = []
    module_elements = accordion.select("dl")

    for modulo_index, dl in enumerate(module_elements, 1):
        title_el = dl.select_one("dt h3")
        modulo_name = title_el.get_text(strip=True) if title_el else f"Módulo {modulo_index}"

        lesson_links = dl.select(f"dd div.item a[href*='{LESSON_HREF_PATTERN}']")

        for aula_index, link in enumerate(lesson_links, 1):
            href = link.get("href", "").strip()
            url = href if href.startswith("http") else f"{base_url}/{href.lstrip('/')}"

            h6 = link.select_one("li h6, h6")
            titulo = h6.get_text(strip=True) if h6 else ""
            if not titulo:
                continue

            lessons.append(
                Lesson(
                    url=url,
                    titulo=titulo,
                    modulo=modulo_name,
                    modulo_index=modulo_index,
                    aula_index=aula_index,
                )
            )

    return lessons
