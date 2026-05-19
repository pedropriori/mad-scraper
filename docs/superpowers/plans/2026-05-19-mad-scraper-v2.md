# MAD Scraper v2 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend MAD Scraper v1 with an interactive CLI (questionary menu + rich live dashboard), named download speed profiles, attachment (Anexos) downloads, headless background scraping, and a complete GitHub-ready README.

**Architecture:** `cli.py` is the new entry point with a questionary menu; `mad_scraper/dashboard.py` drives `rich.Live` during scraping; `scraper.py` is updated to use `DashboardState` and pass progress callbacks to yt-dlp; new `Attachment` model + extractor/writer logic handles course file attachments; `AUTH_HEADLESS` and updated `HEADLESS` default make scraping run in background after login.

**Tech Stack:** Python 3.11+, Rich (Live, Panel, Table, Group), questionary, requests (attachment downloads), yt-dlp Python API, Playwright (headless), pytest

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `requirements.txt` | Modify | Add `questionary>=2.0`, `requests>=2.31` |
| `mad_scraper/config.py` | Modify | Add `AUTH_HEADLESS`, `CONCURRENT_FRAGMENTS`; change `HEADLESS` default → `true` |
| `mad_scraper/auth.py` | Modify | Use `AUTH_HEADLESS` instead of hardcoded `True` |
| `mad_scraper/models.py` | Modify | Add `Attachment` dataclass; add `anexos` field to `LessonContent` |
| `mad_scraper/downloader.py` | Modify | Add `SPEED_PROFILES`, `get_fragment_count()`, `on_progress` param, `download_attachment()` |
| `mad_scraper/extractor.py` | Modify | Add `_get_attachments()`, call it from `_parse_html()` |
| `mad_scraper/writer.py` | Modify | Add `## Anexos` section to `_write_nota()` when attachments present |
| `mad_scraper/dashboard.py` | Create | `DashboardState`, `HistoryEntry`, `Dashboard` with `rich.Live` 3-panel display |
| `scraper.py` | Modify | Use `Dashboard`, pass `on_progress` to `download_video()`, download attachments |
| `cli.py` | Create | questionary menu: run / retry / status / speed settings / exit |
| `.env.example` | Modify | Add `AUTH_HEADLESS`, `HEADLESS`, `CONCURRENT_FRAGMENTS` |
| `README.md` | Create | Full project documentation |
| `tests/test_auth.py` | Modify | Add test for `AUTH_HEADLESS` flag |
| `tests/test_downloader.py` | Modify | Add tests for speed profiles and `download_attachment()` |
| `tests/test_extractor.py` | Modify | Add tests for `_get_attachments()` |
| `tests/test_writer.py` | Modify | Add tests for `LessonContent.anexos` default and nota.md Anexos section |
| `tests/test_dashboard.py` | Create | Unit tests for `DashboardState` |

---

### Task 1: Install New Dependencies

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add new packages to requirements.txt**

Open `requirements.txt` and add at the end:

```
questionary>=2.0
requests>=2.31
```

Full `requirements.txt` after change:
```
playwright>=1.44
yt-dlp>=2024.5.0
beautifulsoup4>=4.12
python-dotenv>=1.0.0
rich>=13.0
pytest>=8.0
pytest-mock>=3.12
questionary>=2.0
requests>=2.31
```

- [ ] **Step 2: Install**

```bash
pip install questionary requests
```

Expected: both install without errors.

- [ ] **Step 3: Verify**

```bash
python -c "import questionary; print('questionary', questionary.__version__)"
python -c "import requests; print('requests', requests.__version__)"
```

Expected: version numbers printed.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore: add questionary and requests dependencies"
```

---

### Task 2: Config and Auth Headless

**Files:**
- Modify: `mad_scraper/config.py`
- Modify: `mad_scraper/auth.py`
- Modify: `tests/test_auth.py`
- Modify: `.env.example`

- [ ] **Step 1: Write the failing test**

Add this test to `tests/test_auth.py` (after the existing 4 tests):

```python
def test_login_respects_auth_headless_flag(tmp_path):
    cookies_path = tmp_path / "cookies.json"
    mock_context = MagicMock()
    mock_context.cookies.return_value = [_cookie()]
    mock_page = MagicMock()
    mock_page.context = mock_context
    mock_browser = MagicMock()
    mock_browser.new_page.return_value = mock_page
    mock_pw = MagicMock()
    mock_pw.chromium.launch.return_value = mock_browser

    with patch("mad_scraper.auth.sync_playwright") as mock_sp, \
         patch("mad_scraper.auth.AUTH_HEADLESS", False):
        mock_sp.return_value.__enter__.return_value = mock_pw
        auth.login("user@email.com", "pass", cookies_path)

    mock_pw.chromium.launch.assert_called_once_with(headless=False)
```

- [ ] **Step 2: Run test — verify it fails**

```bash
pytest tests/test_auth.py::test_login_respects_auth_headless_flag -v
```

Expected: `ImportError` or `AssertionError` (AUTH_HEADLESS not yet defined).

- [ ] **Step 3: Update mad_scraper/config.py**

Replace the existing file entirely:

```python
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://mentoriaamericandr.astronmembers.com"
COURSE_URL = f"{BASE_URL}/curso/mentoria-american-dream"
LOGIN_URL = f"{BASE_URL}/entrar"

COOKIES_PATH = Path(".cookies.json")
LOGIN_EMAIL: str = os.getenv("LOGIN_EMAIL", "")
LOGIN_PASSWORD: str = os.getenv("LOGIN_PASSWORD", "")
OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "mentoria-american-dream"))

# AUTH_HEADLESS=false → browser visible for login (safe for captcha/2FA)
AUTH_HEADLESS: bool = os.getenv("AUTH_HEADLESS", "false").lower() == "true"

# HEADLESS=true → scraping runs in background (default changed from v1)
HEADLESS: bool = os.getenv("HEADLESS", "true").lower() == "true"

# concurrent_fragment_downloads for yt-dlp HLS download
CONCURRENT_FRAGMENTS: int = int(os.getenv("CONCURRENT_FRAGMENTS", "32"))
```

- [ ] **Step 4: Update mad_scraper/auth.py**

Replace the existing file entirely:

```python
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
```

- [ ] **Step 5: Run all auth tests — verify they pass**

```bash
pytest tests/test_auth.py -v
```

Expected: 5 tests PASSED (4 existing + 1 new).

- [ ] **Step 6: Update .env.example**

Replace the existing file entirely:

```
LOGIN_EMAIL=seu@email.com
LOGIN_PASSWORD=sua_senha
OUTPUT_DIR=mentoria-american-dream

# Browser: false = visível (mostra janela), true = invisível (background)
AUTH_HEADLESS=false   # browser abre só durante o login (~5s)
HEADLESS=true         # scraping inteiro roda em background

# Velocidade de download — perfis: eco | normal | fast | ultra
# eco=4 (~20 Mbps)  normal=16 (~76 Mbps)  fast=32 (~222 Mbps)  ultra=64 (experimental)
CONCURRENT_FRAGMENTS=32
```

- [ ] **Step 7: Commit**

```bash
git add mad_scraper/config.py mad_scraper/auth.py tests/test_auth.py .env.example
git commit -m "feat: add AUTH_HEADLESS, CONCURRENT_FRAGMENTS; scraping headless by default"
```

---

### Task 3: Models — Attachment Dataclass

**Files:**
- Modify: `mad_scraper/models.py`
- Modify: `tests/test_writer.py`

- [ ] **Step 1: Write failing tests**

Add these two tests at the end of `tests/test_writer.py`. Also add `Attachment` to the import line at the top:

```python
# Change the import line at the top:
from mad_scraper.models import Lesson, Comment, LessonContent, Attachment
```

Add at the end of `tests/test_writer.py`:

```python
def test_lesson_content_defaults_anexos_to_empty_list():
    lesson = Lesson(
        url="http://x.com", titulo="T", modulo="M", modulo_index=1, aula_index=1
    )
    content = LessonContent(lesson=lesson, descricao="", comentarios=[], panda_embed_url="")
    assert content.anexos == []


def test_attachment_dataclass_fields():
    att = Attachment(nome="apostila.pdf", url="https://cdn.example.com/apostila.pdf")
    assert att.nome == "apostila.pdf"
    assert att.url == "https://cdn.example.com/apostila.pdf"
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_writer.py::test_lesson_content_defaults_anexos_to_empty_list tests/test_writer.py::test_attachment_dataclass_fields -v
```

Expected: `ImportError: cannot import name 'Attachment'`.

- [ ] **Step 3: Update mad_scraper/models.py**

Replace the existing file entirely:

```python
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Lesson:
    url: str
    titulo: str
    modulo: str
    modulo_index: int
    aula_index: int


@dataclass
class Comment:
    autor: str
    data: str
    texto: str


@dataclass
class Attachment:
    nome: str
    url: str


@dataclass
class LessonContent:
    lesson: Lesson
    descricao: str
    comentarios: list[Comment]
    panda_embed_url: str
    duracao_segundos: Optional[int] = None
    anexos: list[Attachment] = field(default_factory=list)
```

- [ ] **Step 4: Run all tests — verify they pass**

```bash
pytest tests/ -v
```

Expected: all 44 tests PASSED (42 existing + 2 new).

- [ ] **Step 5: Commit**

```bash
git add mad_scraper/models.py tests/test_writer.py
git commit -m "feat: add Attachment model and LessonContent.anexos field"
```

---

### Task 4: Downloader — Speed Profiles and Attachment Download

**Files:**
- Modify: `mad_scraper/downloader.py`
- Modify: `tests/test_downloader.py`

- [ ] **Step 1: Write failing tests**

Replace `tests/test_downloader.py` entirely (keeps existing 5 tests, adds 6 new):

```python
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from mad_scraper import downloader

COOKIES = [{
    "name": "session", "value": "abc123", "domain": ".astronmembers.com",
    "path": "/", "secure": True, "expires": 9999999999,
}]
EMBED_URL = "https://player-vz-abc.tv.pandavideo.com.br/embed/?v=xyz"


def _ydl_mock(download_return: int = 0):
    m = MagicMock()
    m.__enter__.return_value = m
    m.download.return_value = download_return
    return m


# ── Existing tests (unchanged) ──────────────────────────────────────────────

def test_returns_true_on_success(tmp_path):
    with patch("mad_scraper.downloader.yt_dlp.YoutubeDL", return_value=_ydl_mock(0)):
        assert downloader.download_video(EMBED_URL, tmp_path, COOKIES) is True


def test_returns_false_on_failure(tmp_path):
    with patch("mad_scraper.downloader.yt_dlp.YoutubeDL", return_value=_ydl_mock(1)):
        assert downloader.download_video(EMBED_URL, tmp_path, COOKIES) is False


def test_passes_video_url_to_ytdlp(tmp_path):
    mock_ydl = _ydl_mock()
    with patch("mad_scraper.downloader.yt_dlp.YoutubeDL", return_value=mock_ydl):
        downloader.download_video(EMBED_URL, tmp_path, COOKIES)
    mock_ydl.download.assert_called_once_with([EMBED_URL])


def test_output_path_in_opts(tmp_path):
    captured: dict = {}

    def fake_ydl(opts):
        captured.update(opts)
        return _ydl_mock()

    with patch("mad_scraper.downloader.yt_dlp.YoutubeDL", side_effect=fake_ydl):
        downloader.download_video(EMBED_URL, tmp_path, COOKIES)

    assert str(tmp_path) in captured.get("outtmpl", "")


def test_cleans_up_temp_cookie_file(tmp_path):
    with patch("mad_scraper.downloader.yt_dlp.YoutubeDL", return_value=_ydl_mock()):
        downloader.download_video(EMBED_URL, tmp_path, COOKIES)
    assert len(list(tmp_path.glob(".tmp_cookies*"))) == 0


# ── New tests ────────────────────────────────────────────────────────────────

def test_get_fragment_count_known_profiles():
    assert downloader.get_fragment_count("eco") == 4
    assert downloader.get_fragment_count("normal") == 16
    assert downloader.get_fragment_count("fast") == 32
    assert downloader.get_fragment_count("ultra") == 64


def test_get_fragment_count_unknown_profile_falls_back_to_config(monkeypatch):
    monkeypatch.setattr(downloader, "CONCURRENT_FRAGMENTS", 16)
    assert downloader.get_fragment_count("invalid") == 16


def test_get_fragment_count_none_falls_back_to_config(monkeypatch):
    monkeypatch.setattr(downloader, "CONCURRENT_FRAGMENTS", 8)
    assert downloader.get_fragment_count(None) == 8


def test_on_progress_hook_included_in_opts(tmp_path):
    captured: dict = {}

    def fake_ydl(opts):
        captured.update(opts)
        return _ydl_mock()

    callback = MagicMock()
    with patch("mad_scraper.downloader.yt_dlp.YoutubeDL", side_effect=fake_ydl):
        downloader.download_video(EMBED_URL, tmp_path, COOKIES, on_progress=callback)

    assert callback in captured.get("progress_hooks", [])


def test_download_attachment_creates_file(tmp_path):
    with patch("mad_scraper.downloader.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.iter_content.return_value = [b"hello world"]
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        result = downloader.download_attachment(
            "https://cdn.example.com/apostila.pdf", tmp_path / "anexos", COOKIES
        )
    assert result is True
    assert (tmp_path / "anexos" / "apostila.pdf").exists()


def test_download_attachment_returns_false_on_error(tmp_path):
    with patch("mad_scraper.downloader.requests.get") as mock_get:
        mock_get.side_effect = Exception("connection error")
        result = downloader.download_attachment(
            "https://cdn.example.com/arquivo.pdf", tmp_path / "anexos", COOKIES
        )
    assert result is False
```

- [ ] **Step 2: Run tests — verify new ones fail**

```bash
pytest tests/test_downloader.py -v
```

Expected: 5 PASSED (existing), 6 FAILED (new — functions not yet defined).

- [ ] **Step 3: Update mad_scraper/downloader.py**

Replace the existing file entirely:

```python
import yt_dlp
import requests
from pathlib import Path
from typing import Callable, Optional

from .auth import cookies_to_netscape
from .config import CONCURRENT_FRAGMENTS

_REFERER = "https://mentoriaamericandr.astronmembers.com"

SPEED_PROFILES: dict[str, int] = {
    "eco": 4,       # ~20 Mbps — gentle, slow/shared connections
    "normal": 16,   # ~76 Mbps — balanced everyday use
    "fast": 32,     # ~222 Mbps — validated default
    "ultra": 64,    # experimental — gigabit connections
}


def get_fragment_count(profile: Optional[str] = None) -> int:
    if profile and profile in SPEED_PROFILES:
        return SPEED_PROFILES[profile]
    return CONCURRENT_FRAGMENTS


def download_video(
    video_url: str,
    lesson_dir: Path,
    cookies: list[dict],
    retries: int = 2,
    on_progress: Optional[Callable] = None,
    speed_profile: Optional[str] = None,
) -> bool:
    cookies_file = lesson_dir / ".tmp_cookies.txt"
    cookies_file.write_text(cookies_to_netscape(cookies), encoding="utf-8")
    try:
        hooks = [on_progress] if on_progress else []
        opts = {
            "cookiefile": str(cookies_file),
            "outtmpl": str(lesson_dir / "video.%(ext)s"),
            "retries": retries,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "overwrites": True,
            "concurrent_fragment_downloads": get_fragment_count(speed_profile),
            "http_headers": {"Referer": _REFERER},
            "progress_hooks": hooks,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.download([video_url]) == 0
    except Exception:
        return False
    finally:
        cookies_file.unlink(missing_ok=True)


def download_attachment(
    url: str,
    dest_dir: Path,
    cookies: list[dict],
    retries: int = 2,
) -> bool:
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = url.split("/")[-1].split("?")[0] or "anexo"
    dest_path = dest_dir / filename
    session_cookies = {c["name"]: c["value"] for c in cookies}
    headers = {"Referer": _REFERER}
    for attempt in range(retries + 1):
        try:
            resp = requests.get(
                url, cookies=session_cookies, headers=headers, timeout=30, stream=True
            )
            resp.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except Exception:
            if attempt == retries:
                return False
    return False
```

- [ ] **Step 4: Run all tests — verify they pass**

```bash
pytest tests/test_downloader.py -v
```

Expected: 11 tests PASSED.

- [ ] **Step 5: Run full suite to check no regressions**

```bash
pytest tests/ -v
```

Expected: all 50 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add mad_scraper/downloader.py tests/test_downloader.py
git commit -m "feat: add download speed profiles and attachment download to downloader"
```

---

### Task 5: Extractor — Anexos Extraction

**Files:**
- Modify: `mad_scraper/extractor.py`
- Modify: `tests/test_extractor.py`

- [ ] **Step 1: Write failing tests**

Add these constants and tests to `tests/test_extractor.py` (after the existing 7 tests).
Also add `Attachment` to the import line:

```python
# Change import line at top of file:
from mad_scraper.models import Lesson, Attachment
```

Add new HTML constants and tests at the end of the file:

```python
MOCK_HTML_WITH_ANEXOS = """
<html><body>
  <div class="videohead"><h6>Aula com Anexos</h6></div>
  <div class="videodesc">Descrição da aula.</div>
  <iframe class="streaming-video-url"
          data-original-url="https://player.pandavideo.com.br/embed/?v=xyz">
  </iframe>
  <div class="lesson-body">
    <h3>Anexos</h3>
    <ul>
      <li><a href="https://cdn.example.com/apostila.pdf">Apostila do Módulo</a></li>
      <li><a href="https://cdn.example.com/swipe-file.zip">Swipe File</a></li>
    </ul>
  </div>
</body></html>
"""

MOCK_HTML_NO_ANEXOS = """
<html><body>
  <div class="videohead"><h6>Aula Sem Anexos</h6></div>
  <div class="videodesc">Só descrição aqui.</div>
  <iframe class="streaming-video-url"
          data-original-url="https://player.pandavideo.com.br/embed/?v=xyz">
  </iframe>
</body></html>
"""


def test_parse_returns_attachments_when_present():
    content = extractor._parse_html(MOCK_HTML_WITH_ANEXOS, _lesson())
    assert len(content.anexos) == 2
    assert content.anexos[0].nome == "Apostila do Módulo"
    assert "apostila.pdf" in content.anexos[0].url


def test_parse_returns_empty_attachments_when_no_section():
    content = extractor._parse_html(MOCK_HTML_NO_ANEXOS, _lesson())
    assert content.anexos == []


def test_get_attachments_empty_html():
    from bs4 import BeautifulSoup
    soup = BeautifulSoup("<html><body><p>Sem anexos</p></body></html>", "html.parser")
    assert extractor._get_attachments(soup) == []
```

- [ ] **Step 2: Run tests — verify new ones fail**

```bash
pytest tests/test_extractor.py -v
```

Expected: 7 PASSED (existing), 3 FAILED (new — `_get_attachments` not yet defined).

- [ ] **Step 3: Update mad_scraper/extractor.py**

Replace the existing file entirely:

```python
import logging
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from .config import HEADLESS
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
    for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        text = heading.get_text(strip=True).lower()
        if "anexo" in text or "arquivo" in text:
            container = heading.parent
            attachments = _collect_file_links(container)
            if attachments:
                return attachments

    # Fallback: search within the lesson content area only
    content_el = soup.select_one(".videodesc")
    if content_el:
        parent = content_el.parent or content_el
        return _collect_file_links(parent)

    return []


def _collect_file_links(container) -> list[Attachment]:
    attachments = []
    for link in container.find_all("a", href=True):
        href = link.get("href", "")
        href_lower = href.lower().split("?")[0]
        if any(href_lower.endswith(ext) for ext in _ATTACHMENT_EXTS):
            nome = link.get_text(strip=True) or href.split("/")[-1]
            attachments.append(Attachment(nome=nome, url=href))
    return attachments
```

- [ ] **Step 4: Run all extractor tests — verify they pass**

```bash
pytest tests/test_extractor.py -v
```

Expected: 10 tests PASSED.

- [ ] **Step 5: Run full suite**

```bash
pytest tests/ -v
```

Expected: all 53 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add mad_scraper/extractor.py tests/test_extractor.py
git commit -m "feat: add attachment extraction to extractor"
```

---

### Task 6: Writer — Anexos Section in nota.md

**Files:**
- Modify: `mad_scraper/writer.py`
- Modify: `tests/test_writer.py`

- [ ] **Step 1: Write failing tests**

Add these tests at the end of `tests/test_writer.py`:

```python
def _content_with_anexos(**kwargs):
    from mad_scraper.models import Attachment
    base = _content(**kwargs)
    base.anexos = [
        Attachment(nome="Apostila.pdf", url="https://cdn.example.com/apostila.pdf"),
        Attachment(nome="Swipe File.zip", url="https://cdn.example.com/swipe-file.zip"),
    ]
    return base


def test_nota_md_has_anexos_section(tmp_path):
    lesson_dir = writer.write_lesson(_content_with_anexos(), tmp_path)
    text = (lesson_dir / "nota.md").read_text(encoding="utf-8")
    assert "## Anexos" in text
    assert "Apostila.pdf" in text
    assert "Swipe File.zip" in text


def test_nota_md_no_anexos_section_when_empty(tmp_path):
    lesson_dir = writer.write_lesson(_content(), tmp_path)
    text = (lesson_dir / "nota.md").read_text(encoding="utf-8")
    assert "## Anexos" not in text


def test_nota_md_anexos_links_are_relative(tmp_path):
    lesson_dir = writer.write_lesson(_content_with_anexos(), tmp_path)
    text = (lesson_dir / "nota.md").read_text(encoding="utf-8")
    assert "anexos/apostila.pdf" in text  # filename derived from URL (lowercase)
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_writer.py::test_nota_md_has_anexos_section tests/test_writer.py::test_nota_md_no_anexos_section_when_empty tests/test_writer.py::test_nota_md_anexos_links_are_relative -v
```

Expected: 3 FAILED.

- [ ] **Step 3: Update mad_scraper/writer.py**

Replace the existing file entirely:

```python
import json
import re
from datetime import datetime
from pathlib import Path

from .models import LessonContent


def write_lesson(content: LessonContent, output_dir: Path) -> Path:
    lesson_dir = _lesson_dir(content, output_dir)
    lesson_dir.mkdir(parents=True, exist_ok=True)
    _write_metadata(content, lesson_dir)
    _write_comentarios(content, lesson_dir)
    _write_nota(content, lesson_dir)
    return lesson_dir


def _lesson_dir(content: LessonContent, output_dir: Path) -> Path:
    modulo_slug = _slugify(f"modulo-{content.lesson.modulo_index:02d}-{content.lesson.modulo}")
    aula_slug = _slugify(f"aula-{content.lesson.aula_index:02d}-{content.lesson.titulo}")
    return output_dir / modulo_slug / aula_slug


def _write_metadata(content: LessonContent, lesson_dir: Path) -> None:
    data = {
        "titulo": content.lesson.titulo,
        "modulo": content.lesson.modulo,
        "modulo_index": content.lesson.modulo_index,
        "aula_index": content.lesson.aula_index,
        "curso": "Mentoria American Dream",
        "url": content.lesson.url,
        "data_download": datetime.now().isoformat(timespec="seconds"),
        "duracao_segundos": content.duracao_segundos,
    }
    (lesson_dir / "metadata.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _write_comentarios(content: LessonContent, lesson_dir: Path) -> None:
    data = [{"autor": c.autor, "data": c.data, "texto": c.texto} for c in content.comentarios]
    (lesson_dir / "comentarios.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _write_nota(content: LessonContent, lesson_dir: Path) -> None:
    modulo_tag = _slugify(f"modulo-{content.lesson.modulo_index:02d}")
    lines = [
        "---",
        f'titulo: "{content.lesson.titulo}"',
        f'modulo: "{content.lesson.modulo}"',
        'curso: "Mentoria American Dream"',
        f'data_download: "{datetime.now().date()}"',
        f'url: "{content.lesson.url}"',
        f"tags: [mentoria, american-dream, {modulo_tag}]",
        "---",
        "",
        f"# {content.lesson.titulo}",
        "",
        "## Descrição",
        content.descricao,
    ]
    if content.comentarios:
        lines += ["", "## Comentários"]
        for c in content.comentarios:
            lines += ["", f"**{c.autor}** · {c.data}", f"> {c.texto}"]
    if content.anexos:
        lines += ["", "## Anexos"]
        for a in content.anexos:
            filename = a.url.split("/")[-1].split("?")[0] or a.nome
            lines.append(f"- [{a.nome}](anexos/{filename})")
    (lesson_dir / "nota.md").write_text("\n".join(lines), encoding="utf-8")


def _slugify(text: str) -> str:
    table = str.maketrans(
        "àáâãäåèéêëìíîïòóôõöùúûüçñ",
        "aaaaaaeeeeiiiioooooouuuucn",
    )
    text = text.lower().translate(table)
    text = re.sub(r"[^a-z0-9\-]", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")
```

- [ ] **Step 4: Run all writer tests — verify they pass**

```bash
pytest tests/test_writer.py -v
```

Expected: 16 tests PASSED (11 existing + 2 model + 3 new).

- [ ] **Step 5: Run full suite**

```bash
pytest tests/ -v
```

Expected: all 56 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add mad_scraper/writer.py tests/test_writer.py
git commit -m "feat: add Anexos section to nota.md when attachments present"
```

---

### Task 7: Dashboard — Live Display

**Files:**
- Create: `mad_scraper/dashboard.py`
- Create: `tests/test_dashboard.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_dashboard.py`:

```python
import pytest
from mad_scraper.dashboard import DashboardState, HistoryEntry


def test_dashboard_state_defaults():
    state = DashboardState(total=107)
    assert state.current == 0
    assert state.current_titulo == ""
    assert state.phase == "aguardando"
    assert state.dl_pct == 0.0
    assert state.history == []


def test_add_history_appends_entry():
    state = DashboardState(total=107)
    state.add_history(HistoryEntry(index=1, titulo="Aula 1", status="done"))
    assert len(state.history) == 1
    assert state.history[0].titulo == "Aula 1"


def test_add_history_caps_at_15():
    state = DashboardState(total=107)
    for i in range(20):
        state.add_history(HistoryEntry(index=i, titulo=f"Aula {i}", status="done"))
    assert len(state.history) == 15


def test_add_history_keeps_most_recent():
    state = DashboardState(total=107)
    for i in range(20):
        state.add_history(HistoryEntry(index=i, titulo=f"Aula {i}", status="done"))
    assert state.history[-1].titulo == "Aula 19"
    assert state.history[0].titulo == "Aula 5"


def test_history_entry_defaults():
    entry = HistoryEntry(index=1, titulo="Aula 1", status="done")
    assert entry.duration_sec == 0
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_dashboard.py -v
```

Expected: `ImportError` — module not yet created.

- [ ] **Step 3: Create mad_scraper/dashboard.py**

```python
from dataclasses import dataclass, field
from typing import Optional

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table


@dataclass
class HistoryEntry:
    index: int
    titulo: str
    status: str   # "done" | "skip" | "failed"
    duration_sec: int = 0


@dataclass
class DashboardState:
    total: int
    current: int = 0
    current_titulo: str = ""
    current_modulo: str = ""
    phase: str = "aguardando"   # "scraping" | "download" | "anexos" | "skip" | "aguardando"
    dl_pct: float = 0.0
    dl_speed_mbps: float = 0.0
    dl_eta_sec: int = 0
    history: list[HistoryEntry] = field(default_factory=list)

    def add_history(self, entry: HistoryEntry) -> None:
        self.history.append(entry)
        if len(self.history) > 15:
            self.history = self.history[-15:]


class Dashboard:
    def __init__(self, state: DashboardState, console: Optional[Console] = None):
        self._state = state
        self._console = console or Console(highlight=False)
        self._live: Optional[Live] = None

    def __enter__(self) -> "Dashboard":
        self._live = Live(
            self._render(),
            console=self._console,
            refresh_per_second=4,
        )
        self._live.__enter__()
        return self

    def __exit__(self, *args) -> None:
        if self._live:
            self._live.__exit__(*args)
            self._live = None

    def refresh(self) -> None:
        if self._live:
            self._live.update(self._render())

    def _render(self) -> Group:
        s = self._state

        # Panel 1: Overall progress
        pct = (s.current / s.total * 100) if s.total else 0
        bar_filled = int(pct / 5)
        bar = "█" * bar_filled + "░" * (20 - bar_filled)
        status_line = (
            f"[bold]{s.current_modulo}[/bold]  ·  {s.current_titulo}"
            if s.current_titulo
            else "[dim]Aguardando...[/dim]"
        )
        progress_panel = Panel(
            f"{status_line}\n  {bar}  {s.current}/{s.total}  {pct:.0f}%",
            title="[bold blue]MAD Scraper — Progresso geral[/bold blue]",
        )

        # Panel 2: Current download
        if s.phase == "download" and s.dl_pct > 0:
            dl_filled = int(s.dl_pct / 5)
            dl_bar = "█" * dl_filled + "░" * (20 - dl_filled)
            speed_str = f"  {s.dl_speed_mbps:.0f} Mbps" if s.dl_speed_mbps else ""
            eta_str = f"  {s.dl_eta_sec}s restando" if s.dl_eta_sec else ""
            dl_body = f"  {dl_bar}  {s.dl_pct:.0f}%{speed_str}{eta_str}"
        else:
            dl_body = f"  [dim]{s.phase}...[/dim]"
        download_panel = Panel(
            f"  [bold]{s.current_titulo or '—'}[/bold]\n{dl_body}",
            title="[bold]Download atual[/bold]",
        )

        # Panel 3: History table
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("", width=2)
        table.add_column("Aula", no_wrap=True, max_width=55)
        table.add_column("", justify="right", width=6)
        _icons = {
            "done": ("✓", "green"),
            "skip": ("–", "dim"),
            "failed": ("✗", "red"),
        }
        for entry in reversed(s.history):
            icon, style = _icons.get(entry.status, ("?", "white"))
            dur = f"{entry.duration_sec}s" if entry.duration_sec else ""
            table.add_row(
                f"[{style}]{icon}[/{style}]",
                f"[{style}]{entry.titulo[:55]}[/{style}]",
                f"[dim]{dur}[/dim]",
            )
        history_panel = Panel(table, title="[bold]Histórico[/bold]")

        return Group(progress_panel, download_panel, history_panel)
```

- [ ] **Step 4: Run dashboard tests — verify they pass**

```bash
pytest tests/test_dashboard.py -v
```

Expected: 5 tests PASSED.

- [ ] **Step 5: Run full suite**

```bash
pytest tests/ -v
```

Expected: all 61 tests PASSED.

- [ ] **Step 6: Commit**

```bash
git add mad_scraper/dashboard.py tests/test_dashboard.py
git commit -m "feat: add live dashboard with 3-panel rich.Live display"
```

---

### Task 8: Orchestrator — Update scraper.py

**Files:**
- Modify: `scraper.py`

No new tests (orchestration is validated via manual dry-run in the next step).

- [ ] **Step 1: Replace scraper.py**

```python
import sys
import io
import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from rich.console import Console
from rich.panel import Panel

from mad_scraper import auth, discovery, extractor, downloader, writer, progress
from mad_scraper.config import LOGIN_EMAIL, LOGIN_PASSWORD, OUTPUT_DIR, COOKIES_PATH, COURSE_URL, HEADLESS
from mad_scraper.dashboard import Dashboard, DashboardState, HistoryEntry
from mad_scraper.progress import Status

load_dotenv()
if getattr(sys.stdout, 'encoding', '').lower() not in ('utf-8', 'utf_8'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

console = Console(highlight=False)


def _make_progress_callback(state: DashboardState, dash: Dashboard):
    def on_progress(info: dict):
        if info.get("status") != "downloading":
            return
        total = info.get("total_bytes") or info.get("total_bytes_estimate") or 0
        downloaded = info.get("downloaded_bytes") or 0
        speed = info.get("speed") or 0
        eta = info.get("eta") or 0
        state.dl_pct = (downloaded / total * 100) if total else 0
        state.dl_speed_mbps = speed / 1_000_000 if speed else 0
        state.dl_eta_sec = int(eta)
        dash.refresh()
    return on_progress


def run(retry_failed: bool = False, speed_profile: str | None = None) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    progress_path = OUTPUT_DIR / "progress.json"

    if not LOGIN_EMAIL or not LOGIN_PASSWORD:
        console.print("[red]✗ ERRO:[/red] LOGIN_EMAIL e LOGIN_PASSWORD não definidos no .env")
        sys.exit(1)

    console.print(Panel.fit("[bold]MAD Scraper[/bold] — Mentoria American Dream", style="bold blue"))
    console.print()

    with console.status("[cyan]Fazendo login...[/cyan]"):
        try:
            cookies = auth.login(LOGIN_EMAIL, LOGIN_PASSWORD, COOKIES_PATH)
        except Exception as e:
            console.print(f"[red]✗ Login FALHOU:[/red] {e}")
            sys.exit(1)
    console.print("[green]✓[/green] Login concluído")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        try:
            ctx = browser.new_context()
            ctx.add_cookies(cookies)
            page = ctx.new_page()

            with console.status("[cyan]Descobrindo aulas...[/cyan]"):
                try:
                    lessons = discovery.get_lessons_with_page(COURSE_URL, page)
                except Exception as e:
                    console.print(f"[red]✗ Discovery FALHOU:[/red] {e}")
                    sys.exit(1)

            if retry_failed:
                failed_urls = set(progress.get_failed(progress_path))
                lessons = [l for l in lessons if l.url in failed_urls]
                console.print(f"[yellow]↻[/yellow] {len(lessons)} aulas para retentar")
            else:
                console.print(f"[green]✓[/green] {len(lessons)} aulas descobertas")
            if speed_profile:
                console.print(f"[cyan]⚡[/cyan] Velocidade: {speed_profile} ({downloader.get_fragment_count(speed_profile)} fragmentos)")

            console.print()
            total = len(lessons)
            ok = 0
            failed_count = 0

            state = DashboardState(total=total)
            with Dashboard(state, console=console) as dash:
                for i, lesson in enumerate(lessons, 1):
                    state.current = i
                    state.current_titulo = lesson.titulo[:55]
                    state.current_modulo = lesson.modulo
                    start = time.time()

                    if not retry_failed and progress.is_done(progress_path, lesson.url):
                        state.add_history(HistoryEntry(index=i, titulo=lesson.titulo[:50], status="skip"))
                        dash.refresh()
                        ok += 1
                        continue

                    state.phase = "scraping"
                    dash.refresh()

                    try:
                        content = extractor.extract_with_page(lesson, page)
                        lesson_dir = writer.write_lesson(content, OUTPUT_DIR)

                        if not content.panda_embed_url:
                            progress.mark(progress_path, lesson.url, Status.DONE)
                            state.add_history(HistoryEntry(index=i, titulo=lesson.titulo[:50], status="skip"))
                            dash.refresh()
                            ok += 1
                            continue

                        state.phase = "download"
                        state.dl_pct = 0.0
                        dash.refresh()
                        on_prog = _make_progress_callback(state, dash)
                        success = downloader.download_video(
                            content.panda_embed_url,
                            lesson_dir,
                            cookies,
                            on_progress=on_prog,
                            speed_profile=speed_profile,
                        )

                        if content.anexos:
                            state.phase = "anexos"
                            dash.refresh()
                            anexos_dir = lesson_dir / "anexos"
                            for att in content.anexos:
                                downloader.download_attachment(att.url, anexos_dir, cookies)

                        dur = int(time.time() - start)
                        if success:
                            progress.mark(progress_path, lesson.url, Status.DONE)
                            state.add_history(HistoryEntry(
                                index=i, titulo=lesson.titulo[:50], status="done", duration_sec=dur
                            ))
                            ok += 1
                        else:
                            progress.mark(progress_path, lesson.url, Status.FAILED)
                            state.add_history(HistoryEntry(index=i, titulo=lesson.titulo[:50], status="failed"))
                            failed_count += 1

                    except Exception as e:
                        progress.mark(progress_path, lesson.url, Status.FAILED)
                        state.add_history(HistoryEntry(index=i, titulo=lesson.titulo[:50], status="failed"))
                        failed_count += 1

                    dash.refresh()

        finally:
            browser.close()

    console.print()
    console.rule()
    if failed_count:
        console.print(f"[bold]Concluído:[/bold] {ok}/{total} OK  [red]{failed_count} falhas[/red]")
        console.print("[yellow]Rode: python cli.py → Retentar aulas com falha[/yellow]")
    else:
        console.print(f"[bold green]Concluído:[/bold green] {ok}/{total} OK — tudo certo!")


if __name__ == "__main__":
    speed = None
    args = sys.argv[1:]
    if "--speed" in args:
        idx = args.index("--speed")
        if idx + 1 < len(args):
            speed = args[idx + 1]
    run(
        retry_failed="--retry-failed" in sys.argv,
        speed_profile=speed,
    )
```

- [ ] **Step 2: Run full test suite — verify no regressions**

```bash
pytest tests/ -v
```

Expected: all 61 tests PASSED.

- [ ] **Step 3: Dry-run import check**

```bash
python -c "from scraper import run; print('import OK')"
```

Expected: `import OK` (no errors).

- [ ] **Step 4: Commit**

```bash
git add scraper.py
git commit -m "feat: update orchestrator — dashboard, speed profiles, attachment downloads"
```

---

### Task 9: Interactive CLI

**Files:**
- Create: `cli.py`

- [ ] **Step 1: Create cli.py**

```python
#!/usr/bin/env python3
"""MAD Scraper — interactive CLI. Run: python cli.py"""
import sys
import io
from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from mad_scraper.config import OUTPUT_DIR
from mad_scraper.progress import load as load_progress
from mad_scraper.downloader import SPEED_PROFILES, CONCURRENT_FRAGMENTS

if getattr(sys.stdout, 'encoding', '').lower() not in ('utf-8', 'utf_8'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

console = Console(highlight=False)


def _status_summary() -> dict:
    data = load_progress(OUTPUT_DIR / "progress.json")
    return {
        "done": sum(1 for v in data.values() if v == "done"),
        "failed": sum(1 for v in data.values() if v == "failed"),
        "total": len(data),
    }


def _show_progress_table() -> None:
    data = load_progress(OUTPUT_DIR / "progress.json")
    if not data:
        console.print("[yellow]Nenhum progresso registrado ainda.[/yellow]\n")
        return
    done = sum(1 for v in data.values() if v == "done")
    failed = sum(1 for v in data.values() if v == "failed")
    pending = sum(1 for v in data.values() if v == "pending")
    table = Table(title="Progresso Atual", show_lines=False, min_width=35)
    table.add_column("Status", width=18)
    table.add_column("Qtd", justify="right")
    table.add_row("[green]✓  Concluídas[/green]", f"[green]{done}[/green]")
    table.add_row("[red]✗  Com falha[/red]", f"[red]{failed}[/red]")
    table.add_row("[dim]⏳  Pendentes[/dim]", f"[dim]{pending}[/dim]")
    table.add_row("[bold]   Total[/bold]", f"[bold]{len(data)}[/bold]")
    console.print(table)
    console.print()


def _choose_speed() -> str | None:
    choices = [
        questionary.Choice(
            "eco    —  4 fragmentos  (~20 Mbps)   Conexão lenta ou compartilhada",
            value="eco"
        ),
        questionary.Choice(
            "normal — 16 fragmentos  (~76 Mbps)   Uso cotidiano seguro",
            value="normal"
        ),
        questionary.Choice(
            "fast   — 32 fragmentos  (~222 Mbps)  Padrão validado  ★",
            value="fast"
        ),
        questionary.Choice(
            "ultra  — 64 fragmentos  (exp.)       Conexão gigabit+",
            value="ultra"
        ),
        questionary.Choice("← Voltar", value=None),
    ]
    return questionary.select(
        "Escolha o perfil de velocidade:",
        choices=choices,
    ).ask()


def main() -> None:
    console.print(Panel.fit(
        "[bold]MAD Scraper[/bold] — Mentoria American Dream\n"
        "[dim]python cli.py  ·  scraper de cursos offline[/dim]",
        style="bold blue",
    ))
    console.print()

    speed_profile: str | None = None

    while True:
        summary = _status_summary()
        login_ok = Path(".cookies.json").exists()
        login_str = "[green]✓ sessão salva[/green]" if login_ok else "[yellow]⚠ não logado[/yellow]"
        console.print(f"  Login: {login_str}")
        console.print(
            f"  Progresso: [green]{summary['done']} concluídas[/green]  "
            f"[red]{summary['failed']} falhas[/red]  "
            f"[dim]{summary['total']} registradas[/dim]"
        )
        active_frags = SPEED_PROFILES.get(speed_profile, CONCURRENT_FRAGMENTS) if speed_profile else CONCURRENT_FRAGMENTS
        console.print(
            f"  Velocidade: [cyan]{speed_profile or 'padrão'}[/cyan] "
            f"[dim]({active_frags} fragmentos)[/dim]"
        )
        console.print()

        choices = [
            questionary.Choice("▶   Iniciar scraping completo", value="run"),
        ]
        if summary["failed"] > 0:
            choices.append(questionary.Choice(
                f"↻   Retentar aulas com falha ({summary['failed']})", value="retry"
            ))
        choices += [
            questionary.Choice("📊  Ver progresso atual", value="progress"),
            questionary.Choice("⚙   Configurações de download", value="speed"),
            questionary.Choice("✕   Sair", value="exit"),
        ]

        action = questionary.select("O que deseja fazer?", choices=choices).ask()

        if action is None or action == "exit":
            console.print("[dim]Até mais.[/dim]")
            break
        elif action == "run":
            console.print()
            from scraper import run
            run(retry_failed=False, speed_profile=speed_profile)
            break
        elif action == "retry":
            console.print()
            from scraper import run
            run(retry_failed=True, speed_profile=speed_profile)
            break
        elif action == "progress":
            console.print()
            _show_progress_table()
        elif action == "speed":
            console.print()
            chosen = _choose_speed()
            if chosen:
                speed_profile = chosen
                console.print(f"[green]✓[/green] Perfil alterado para [cyan]{chosen}[/cyan]\n")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke test — verify import works**

```bash
python -c "import cli; print('import OK')"
```

Expected: `import OK`.

- [ ] **Step 3: Manual smoke test**

```bash
python cli.py
```

Expected: banner + menu appears. Navigate with arrow keys. Select **Ver progresso atual** → shows table. Select **Configurações de download** → shows profile list. Select **Sair** → exits cleanly.

Do NOT select "Iniciar scraping completo" unless you intend to run the full scrape.

- [ ] **Step 4: Run full test suite — verify no regressions**

```bash
pytest tests/ -v
```

Expected: all 61 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add cli.py
git commit -m "feat: add interactive CLI with questionary menu and speed settings"
```

---

### Task 10: README and .gitignore

**Files:**
- Create: `README.md`
- Modify: `.gitignore`

- [ ] **Step 1: Verify .gitignore covers all sensitive/large files**

Check current `.gitignore`:

```bash
cat .gitignore
```

Ensure these lines are present (add any that are missing):

```
.env
.cookies.json
mentoria-american-dream/
__pycache__/
.pytest_cache/
*.pyc
*.ts
*.mp4
```

- [ ] **Step 2: Create README.md**

```markdown
# MAD Scraper

Download offline completo do curso **Mentoria American Dream** (astronmembers.com + Panda Video) — vídeos, descrições, comentários e anexos organizados em pastas com notas Obsidian.

> Ferramenta de uso pessoal. Requer acesso legítimo ao curso.

---

## Funcionalidades

- Login automatizado via Playwright (browser visível só no login)
- Descoberta automática de todos os módulos e aulas
- Download de vídeos HLS via yt-dlp com até 222 Mbps
- Download de arquivos anexos (PDFs, ZIPs, etc.)
- Notas Obsidian (`.md`) com frontmatter, descrição e comentários
- Progresso resumível — interrompa e continue de onde parou
- CLI interativa com menu, dashboard ao vivo e configurações de velocidade

---

## Pré-requisitos

- Python 3.11+
- pip

---

## Instalação

```bash
git clone <url-do-repo>
cd mad-scraper

pip install -r requirements.txt
playwright install chromium
```

---

## Configuração

```bash
cp .env.example .env
```

Edite `.env`:

| Variável | Padrão | Descrição |
|---|---|---|
| `LOGIN_EMAIL` | — | E-mail da conta no astronmembers.com |
| `LOGIN_PASSWORD` | — | Senha da conta |
| `OUTPUT_DIR` | `mentoria-american-dream` | Pasta de destino dos downloads |
| `AUTH_HEADLESS` | `false` | `false` = browser visível no login (recomendado) |
| `HEADLESS` | `true` | `true` = scraping roda em background |
| `CONCURRENT_FRAGMENTS` | `32` | Fragmentos HLS paralelos (veja perfis abaixo) |

---

## Uso

### CLI Interativa (recomendado)

```bash
python cli.py
```

Menu com setas:
- **Iniciar scraping completo** — baixa todas as aulas (pula as já concluídas)
- **Retentar aulas com falha** — aparece quando há falhas registradas
- **Ver progresso atual** — tabela com done/falhas/pendentes
- **Configurações de download** — seleciona perfil de velocidade
- **Sair**

### Linha de Comando Direta

```bash
# Scraping completo
python scraper.py

# Retentar falhas
python scraper.py --retry-failed

# Especificar perfil de velocidade
python scraper.py --speed normal
```

---

## Perfis de Velocidade

| Perfil | Fragmentos | Velocidade típica | Quando usar |
|---|---|---|---|
| `eco` | 4 | ~20 Mbps | Conexão lenta ou compartilhada |
| `normal` | 16 | ~76 Mbps | Uso cotidiano seguro |
| `fast` | 32 | ~222 Mbps | **Padrão** — validado em produção |
| `ultra` | 64 | experimental | Conexão gigabit+ |

Configure via `.env` (`CONCURRENT_FRAGMENTS=16`) ou via menu da CLI.

---

## Estrutura de Output

```
mentoria-american-dream/
  progress.json                        ← estado de cada aula (resumabilidade)
  modulo-01-nome-do-modulo/
    aula-01-titulo-da-aula/
      video.mp4
      metadata.json
      comentarios.json
      nota.md                          ← nota Obsidian com frontmatter
      anexos/                          ← criado só se houver arquivos
        apostila.pdf
        swipe-file.zip
    aula-02-titulo/
      ...
  modulo-02-nome/
    ...
```

---

## Testes

```bash
pytest tests/ -v
```

61 testes cobrindo progress, writer, auth, discovery, extractor, downloader, dashboard.

---

## Troubleshooting

**Login falha com timeout**
Verifique as credenciais no `.env`. Se houver captcha, tente `AUTH_HEADLESS=false` e resolva manualmente na janela do browser.

**Discovery retorna 0 aulas**
O seletor da sidebar pode ter mudado. Inspecione a página com `HEADLESS=false` e atualize `LESSON_HREF_PATTERN` em `discovery.py`.

**Download falha com 403**
Cookies podem ter expirado. Delete `.cookies.json` e rode novamente — o scraper faz login automaticamente.

**`concurrent_fragment_downloads` alto causa erros**
Reduza para `normal` (16) ou `eco` (4) via CLI ou `.env`.
```

- [ ] **Step 3: Run final test suite**

```bash
pytest tests/ -v
```

Expected: all 61 tests PASSED.

- [ ] **Step 4: Commit**

```bash
git add README.md .gitignore
git commit -m "docs: add README with full usage docs, troubleshooting, and speed profiles"
```

---

## Troubleshooting

**`ImportError: cannot import name 'Attachment'`** — Task 3 não foi executada. Rode `pytest tests/test_writer.py` para verificar.

**`AttributeError: 'DashboardState' object has no attribute 'add_history'`** — Task 7 não foi executada. Verifique `mad_scraper/dashboard.py`.

**questionary menu não aparece no Windows** — Certifique-se que o terminal suporta ANSI (PowerShell ou Windows Terminal). CMD puro pode ter problemas.

**Dashboard renderiza com caracteres estranhos** — Terminal não suporta Unicode. Configure `PYTHONIOENCODING=utf-8` ou use Windows Terminal.

**`rich.console.Group` ImportError** — Versão antiga do rich. Rode `pip install --upgrade rich`.
