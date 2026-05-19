import logging
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from .config import HEADLESS
from .models import Lesson, LessonContent, Comment

TEMPLATE_COMMENT_ID = "{id}"


_QUALITY_PREF = ["1080p", "720p", "480p", "360p"]


def extract_with_page(lesson: Lesson, page) -> LessonContent:
    """Extract lesson content reusing an existing Playwright page (no new browser)."""
    m3u8_by_quality: dict[str, str] = {}

    def _on_request(request):
        url = request.url
        if ".m3u8" not in url or "get_qualities" in url:
            return
        for q in _QUALITY_PREF:
            if f"/{q}/" in url:
                m3u8_by_quality[q] = url
                return

    page.on("request", _on_request)
    try:
        page.goto(lesson.url)
        page.wait_for_load_state("networkidle")
        try:
            page.wait_for_selector("iframe.streaming-video-url", timeout=10000)
            page.wait_for_timeout(3000)  # wait for player to request quality streams
        except Exception as e:
            logging.debug("Video iframe not found (text-only?): %s", e)
        html = page.content()
    finally:
        page.remove_listener("request", _on_request)

    content = _parse_html(html, lesson)
    for quality in _QUALITY_PREF:
        if quality in m3u8_by_quality:
            content.panda_embed_url = m3u8_by_quality[quality]
            break
    return content


def extract(lesson: Lesson, cookies: list[dict]) -> LessonContent:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        try:
            context = browser.new_context()
            context.add_cookies(cookies)
            page = context.new_page()
            page.goto(lesson.url)
            page.wait_for_load_state("networkidle")
            try:
                page.wait_for_selector("iframe.streaming-video-url", timeout=10000)
            except Exception as e:
                logging.debug("Video iframe not found (text-only lesson?): %s", e)
            html = page.content()
        finally:
            browser.close()
    return _parse_html(html, lesson)


def _parse_html(html: str, lesson: Lesson) -> LessonContent:
    soup = BeautifulSoup(html, "html.parser")
    return LessonContent(
        lesson=lesson,
        descricao=_get_description(soup),
        comentarios=_get_comments(soup),
        panda_embed_url=_get_panda_url(soup),
    )


def _get_description(soup: BeautifulSoup) -> str:
    el = soup.select_one(".videodesc")
    return el.get_text(strip=True) if el else ""


def _get_panda_url(soup: BeautifulSoup) -> str:
    iframe = soup.select_one("iframe.streaming-video-url")
    if iframe:
        return iframe.get("data-original-url") or iframe.get("src") or ""
    return ""


def _get_comments(soup: BeautifulSoup) -> list[Comment]:
    comment_els = soup.select("div.comment.comment-box")
    comments = []
    for el in comment_els:
        data_id = el.get("data-id", "")
        if data_id == TEMPLATE_COMMENT_ID:
            continue
        autor_el = el.select_one("h4.name")
        date_el = el.select_one("p.time")
        body_el = el.select_one("p.commentdesc")
        autor = autor_el.get_text(strip=True) if autor_el else "Desconhecido"
        data = date_el.get_text(strip=True) if date_el else ""
        texto = body_el.get_text(strip=True) if body_el else ""
        if texto:
            comments.append(Comment(autor=autor, data=data, texto=texto))
    return comments
