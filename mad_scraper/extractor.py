import logging
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from .config import BASE_URL, HEADLESS
from .models import Lesson, LessonContent, Comment, Attachment

TEMPLATE_COMMENT_ID = "{id}"
_QUALITY_PREF = ["1080p", "720p", "480p", "360p"]
_ATTACHMENT_EXTS = {".pdf", ".zip", ".docx", ".xlsx", ".pptx", ".mp3", ".csv"}


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
            page.wait_for_timeout(3000)
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
        _args = ["--window-position=-32000,-32000"] if HEADLESS else []
        browser = p.chromium.launch(headless=False, args=_args)
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
        anexos=_get_attachments(soup),
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


def _get_attachments(soup: BeautifulSoup) -> list[Attachment]:
    """Find downloadable attachments in an 'Anexos'/'Arquivos' section."""
    # Primary: dedicated anexos panel (astronmembers.com tab structure)
    panel = soup.select_one(".aba-anexos")
    if panel:
        attachments = _collect_download_links(panel)
        if attachments:
            return attachments

    # Secondary: any a[download] link on the page (tab panel loaded after click)
    attachments = _collect_download_links(soup)
    if attachments:
        return attachments

    # Fallback: heading-based search (legacy / other platforms)
    for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        text = heading.get_text(strip=True).lower()
        if "anexo" in text or "arquivo" in text:
            container = heading.parent
            attachments = _collect_file_links(container)
            if attachments:
                return attachments

    content_el = soup.select_one(".videodesc")
    if content_el:
        parent = content_el.parent or content_el
        return _collect_file_links(parent)

    return []


def _collect_download_links(panel) -> list[Attachment]:
    """Collect attachments from the .aba-anexos tab panel (astronmembers.com format)."""
    attachments = []
    for link in panel.select("a.box-anexo-action-download"):
        href = link.get("href", "")
        if not href:
            continue
        url = href if href.startswith("http") else f"{BASE_URL}/{href.lstrip('/')}"
        filename = link.get("download", "") or href.split("/")[-1].split("?")[0]
        box = link.find_parent(class_="box-anexo")
        if box:
            nome_el = box.select_one(".box-anexo-text p")
            nome = nome_el.get_text(strip=True) if nome_el else filename
        else:
            nome = filename
        attachments.append(Attachment(nome=nome, url=url, filename=filename))
    return attachments


def _collect_file_links(container) -> list[Attachment]:
    attachments = []
    for link in container.find_all("a", href=True):
        href = link.get("href", "")
        href_lower = href.lower().split("?")[0]
        if any(href_lower.endswith(ext) for ext in _ATTACHMENT_EXTS):
            nome = link.get_text(strip=True) or href.split("/")[-1]
            attachments.append(Attachment(nome=nome, url=href))
    return attachments
