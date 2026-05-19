# MAD Scraper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI scraper that downloads all ~107 lessons from astronmembers.com (Mentoria American Dream) — vídeo (Panda Video), descrição e comentários — organized into folders with `metadata.json`, `comentarios.json`, and `nota.md` (Obsidian).

**Architecture:** Playwright handles authenticated browsing and returns rendered HTML; BeautifulSoup parses that HTML in pure functions (testable without browser); yt-dlp downloads the Panda Video stream using cookies exported from Playwright; `progress.json` enables resuming interrupted runs. All components are independent modules orchestrated by `scraper.py`.

**Tech Stack:** Python 3.11+, Playwright (browser automation), BeautifulSoup4 (HTML parsing), yt-dlp (video download), python-dotenv (env config), pytest + pytest-mock (testing)

---

## File Map

| File | Responsibility |
|------|----------------|
| `mad_scraper/models.py` | Data classes: `Lesson`, `Comment`, `LessonContent` |
| `mad_scraper/config.py` | Env loading, URL constants, paths |
| `mad_scraper/progress.py` | Read/write `progress.json`, status tracking |
| `mad_scraper/auth.py` | Playwright login, cookie export/load, Netscape conversion |
| `mad_scraper/discovery.py` | Navigate course → rendered HTML → `list[Lesson]` |
| `mad_scraper/extractor.py` | Navigate lesson → rendered HTML → `LessonContent` |
| `mad_scraper/downloader.py` | yt-dlp wrapper, temp cookie file management |
| `mad_scraper/writer.py` | Write `metadata.json`, `comentarios.json`, `nota.md` |
| `scraper.py` | CLI entry point, orchestrates all phases with progress display |
| `tests/test_progress.py` | Unit tests for progress module |
| `tests/test_writer.py` | Unit tests for writer module |
| `tests/test_auth.py` | Unit tests for auth (mocked Playwright) |
| `tests/test_discovery.py` | Unit tests for discovery HTML parsing (BeautifulSoup, no browser) |
| `tests/test_extractor.py` | Unit tests for extractor HTML parsing (BeautifulSoup, no browser) |
| `tests/test_downloader.py` | Unit tests for downloader (mocked subprocess) |

---

### Task 1: Project Setup

**Files:**
- Create: `mad_scraper/__init__.py`
- Create: `tests/__init__.py`
- Create: `requirements.txt`
- Create: `.env.example`

- [ ] **Step 1: Create package structure**

```bash
cd /c/Users/kadil/Documents/Projects/scraping/mad-scraper
mkdir -p mad_scraper tests
touch mad_scraper/__init__.py tests/__init__.py
```

- [ ] **Step 2: Create requirements.txt**

```
playwright>=1.44
yt-dlp>=2024.5.0
beautifulsoup4>=4.12
python-dotenv>=1.0.0
pytest>=8.0
pytest-mock>=3.12
```

- [ ] **Step 3: Create .env.example**

```
LOGIN_EMAIL=seu@email.com
LOGIN_PASSWORD=sua_senha
OUTPUT_DIR=mentoria-american-dream
```

- [ ] **Step 4: Install dependencies**

```bash
pip install -r requirements.txt
playwright install chromium
```

Expected: `chromium` installed successfully.

- [ ] **Step 5: Verify setup**

```bash
python -c "from playwright.sync_api import sync_playwright; print('playwright OK')"
python -c "import yt_dlp; print('yt-dlp OK')"
python -c "from bs4 import BeautifulSoup; print('beautifulsoup OK')"
```

Expected: three `OK` lines.

- [ ] **Step 6: Init git and commit**

```bash
git init
git add requirements.txt .env.example mad_scraper/__init__.py tests/__init__.py
git commit -m "chore: project setup"
```

---

### Task 2: Models and Config

**Files:**
- Create: `mad_scraper/models.py`
- Create: `mad_scraper/config.py`

- [ ] **Step 1: Create mad_scraper/models.py**

```python
from dataclasses import dataclass
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
class LessonContent:
    lesson: Lesson
    descricao: str
    comentarios: list[Comment]
    panda_embed_url: str
    duracao_segundos: Optional[int] = None
```

- [ ] **Step 2: Create mad_scraper/config.py**

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
```

- [ ] **Step 3: Verify imports**

```bash
python -c "from mad_scraper.models import Lesson, Comment, LessonContent; print('OK')"
python -c "from mad_scraper.config import COURSE_URL; print(COURSE_URL)"
```

Expected: `OK` and the full course URL.

- [ ] **Step 4: Commit**

```bash
git add mad_scraper/models.py mad_scraper/config.py
git commit -m "feat: add data models and config"
```

---

### Task 3: Progress Module

**Files:**
- Create: `mad_scraper/progress.py`
- Create: `tests/test_progress.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_progress.py
import pytest
from pathlib import Path
from mad_scraper import progress
from mad_scraper.progress import Status


def test_load_returns_empty_dict_if_no_file(tmp_path):
    assert progress.load(tmp_path / "progress.json") == {}


def test_save_and_load_roundtrip(tmp_path):
    p = tmp_path / "progress.json"
    data = {"https://example.com/aula-1": "done"}
    progress.save(p, data)
    assert progress.load(p) == data


def test_mark_sets_status(tmp_path):
    p = tmp_path / "progress.json"
    progress.mark(p, "https://example.com/aula-1", Status.DONE)
    assert progress.load(p)["https://example.com/aula-1"] == "done"


def test_is_done_returns_true_for_done(tmp_path):
    p = tmp_path / "progress.json"
    progress.mark(p, "https://example.com/aula-1", Status.DONE)
    assert progress.is_done(p, "https://example.com/aula-1") is True


def test_is_done_returns_false_for_failed(tmp_path):
    p = tmp_path / "progress.json"
    progress.mark(p, "https://example.com/aula-1", Status.FAILED)
    assert progress.is_done(p, "https://example.com/aula-1") is False


def test_is_done_returns_false_for_unknown_url(tmp_path):
    assert progress.is_done(tmp_path / "progress.json", "https://example.com/x") is False


def test_get_failed_returns_only_failed_urls(tmp_path):
    p = tmp_path / "progress.json"
    progress.mark(p, "https://example.com/aula-1", Status.DONE)
    progress.mark(p, "https://example.com/aula-2", Status.FAILED)
    progress.mark(p, "https://example.com/aula-3", Status.FAILED)
    assert set(progress.get_failed(p)) == {
        "https://example.com/aula-2",
        "https://example.com/aula-3",
    }


def test_mark_overwrites_existing_status(tmp_path):
    p = tmp_path / "progress.json"
    progress.mark(p, "https://example.com/aula-1", Status.FAILED)
    progress.mark(p, "https://example.com/aula-1", Status.DONE)
    assert progress.is_done(p, "https://example.com/aula-1") is True
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_progress.py -v
```

Expected: `ImportError` — module not yet implemented.

- [ ] **Step 3: Implement mad_scraper/progress.py**

```python
import json
from enum import Enum
from pathlib import Path


class Status(str, Enum):
    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"


def load(progress_path: Path) -> dict:
    if not progress_path.exists():
        return {}
    return json.loads(progress_path.read_text(encoding="utf-8"))


def save(progress_path: Path, data: dict) -> None:
    progress_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def mark(progress_path: Path, lesson_url: str, status: Status) -> None:
    data = load(progress_path)
    data[lesson_url] = status.value
    save(progress_path, data)


def is_done(progress_path: Path, lesson_url: str) -> bool:
    return load(progress_path).get(lesson_url) == Status.DONE.value


def get_failed(progress_path: Path) -> list[str]:
    return [
        url
        for url, status in load(progress_path).items()
        if status == Status.FAILED.value
    ]
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_progress.py -v
```

Expected: 8 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add mad_scraper/progress.py tests/test_progress.py
git commit -m "feat: add progress tracking module"
```

---

### Task 4: Writer Module

**Files:**
- Create: `mad_scraper/writer.py`
- Create: `tests/test_writer.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_writer.py
import json
import pytest
from pathlib import Path
from mad_scraper.models import Lesson, Comment, LessonContent
from mad_scraper import writer


def _content(
    titulo="Aula de Copywriting",
    modulo="Fundamentos",
    modulo_index=1,
    aula_index=3,
    descricao="Descrição da aula.",
    comentarios=None,
    panda_embed_url="https://player.pandavideo.com.br/embed/?v=abc123",
    duracao_segundos=3600,
):
    if comentarios is None:
        comentarios = [Comment(autor="João Silva", data="2026-01-15", texto="Excelente!")]
    lesson = Lesson(
        url="https://mentoriaamericandr.astronmembers.com/curso/mentoria-american-dream/1/3",
        titulo=titulo,
        modulo=modulo,
        modulo_index=modulo_index,
        aula_index=aula_index,
    )
    return LessonContent(
        lesson=lesson,
        descricao=descricao,
        comentarios=comentarios,
        panda_embed_url=panda_embed_url,
        duracao_segundos=duracao_segundos,
    )


def test_creates_lesson_directory(tmp_path):
    lesson_dir = writer.write_lesson(_content(), tmp_path)
    assert lesson_dir.exists()


def test_lesson_dir_naming_convention(tmp_path):
    lesson_dir = writer.write_lesson(_content(), tmp_path)
    assert lesson_dir.name.startswith("aula-03-")
    assert lesson_dir.parent.name.startswith("modulo-01-")


def test_metadata_json_fields(tmp_path):
    lesson_dir = writer.write_lesson(_content(), tmp_path)
    data = json.loads((lesson_dir / "metadata.json").read_text())
    assert data["titulo"] == "Aula de Copywriting"
    assert data["modulo"] == "Fundamentos"
    assert data["modulo_index"] == 1
    assert data["aula_index"] == 3
    assert data["curso"] == "Mentoria American Dream"
    assert data["duracao_segundos"] == 3600


def test_comentarios_json_structure(tmp_path):
    lesson_dir = writer.write_lesson(_content(), tmp_path)
    data = json.loads((lesson_dir / "comentarios.json").read_text())
    assert isinstance(data, list)
    assert data[0]["autor"] == "João Silva"
    assert data[0]["texto"] == "Excelente!"


def test_nota_md_has_frontmatter(tmp_path):
    lesson_dir = writer.write_lesson(_content(), tmp_path)
    text = (lesson_dir / "nota.md").read_text()
    assert text.startswith("---")
    assert "titulo:" in text
    assert "tags:" in text


def test_nota_md_has_descricao(tmp_path):
    lesson_dir = writer.write_lesson(_content(), tmp_path)
    text = (lesson_dir / "nota.md").read_text()
    assert "## Descrição" in text
    assert "Descrição da aula." in text


def test_nota_md_has_comentarios(tmp_path):
    lesson_dir = writer.write_lesson(_content(), tmp_path)
    text = (lesson_dir / "nota.md").read_text()
    assert "## Comentários" in text
    assert "João Silva" in text
    assert "Excelente!" in text


def test_nota_md_no_comentarios_section_when_empty(tmp_path):
    lesson_dir = writer.write_lesson(_content(comentarios=[]), tmp_path)
    text = (lesson_dir / "nota.md").read_text()
    assert "## Comentários" not in text


def test_empty_comentarios_writes_empty_list(tmp_path):
    lesson_dir = writer.write_lesson(_content(comentarios=[]), tmp_path)
    data = json.loads((lesson_dir / "comentarios.json").read_text())
    assert data == []


def test_slugify_handles_accents():
    assert writer._slugify("Módulo Número Um") == "modulo-numero-um"


def test_slugify_handles_special_chars():
    assert writer._slugify("Aula: Estratégia & Copywriting!") == "aula-estrategia-copywriting"
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_writer.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement mad_scraper/writer.py**

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

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_writer.py -v
```

Expected: 11 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add mad_scraper/writer.py tests/test_writer.py
git commit -m "feat: add writer module with Obsidian markdown output"
```

---

### Task 5: HTML Inspection (Manual — required before Tasks 6–8)

Before implementing auth, discovery, and extractor, inspect the actual HTML to get correct selectors. This task produces no committed code.

- [ ] **Step 1: Create inspect_site.py**

```python
# inspect_site.py
import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

EMAIL = os.getenv("LOGIN_EMAIL")
PASSWORD = os.getenv("LOGIN_PASSWORD")
COURSE_URL = "https://mentoriaamericandr.astronmembers.com/curso/mentoria-american-dream"
LESSON_URL = "https://mentoriaamericandr.astronmembers.com/curso/mentoria-american-dream/125393/707026"


with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()

    print("\n=== LOGIN PAGE ===")
    page.goto("https://mentoriaamericandr.astronmembers.com/entrar")
    page.wait_for_load_state("networkidle")
    inputs = page.query_selector_all("input")
    print("Input types:", [el.get_attribute("type") for el in inputs])
    submit = page.query_selector("button[type='submit'], input[type='submit']")
    print("Submit selector found:", submit is not None)

    page.fill("input[type='email']", EMAIL)
    page.fill("input[type='password']", PASSWORD)
    page.click("button[type='submit']")
    page.wait_for_load_state("networkidle")
    print("Post-login URL:", page.url)

    print("\n=== COURSE PAGE ===")
    page.goto(COURSE_URL)
    page.wait_for_load_state("networkidle")
    lesson_links = page.query_selector_all("a[href*='mentoria-american-dream']")
    print(f"Lesson links found: {len(lesson_links)}")
    for link in lesson_links[:5]:
        print(f"  href={link.get_attribute('href')!r}  text={link.inner_text().strip()[:60]!r}")

    # Print first 2000 chars of body to inspect structure
    body_html = page.inner_html("body")
    print("\nBody HTML (first 2000 chars):")
    print(body_html[:2000])

    print("\n=== LESSON PAGE ===")
    page.goto(LESSON_URL)
    page.wait_for_load_state("networkidle")

    iframes = page.query_selector_all("iframe")
    print(f"Iframes found: {len(iframes)}")
    for iframe in iframes:
        print(f"  src={iframe.get_attribute('src')!r}")

    # Try common description selectors
    for sel in ["[class*='description']", "[class*='content']", "article", ".lesson"]:
        el = page.query_selector(sel)
        if el:
            print(f"\nDescription candidate '{sel}':")
            print(el.inner_text()[:300])
            break

    # Try common comment selectors
    for sel in ["[class*='comment']", ".comments", "#comments"]:
        items = page.query_selector_all(sel)
        if items:
            print(f"\nComment selector '{sel}' found {len(items)} items")
            print("First item HTML:", items[0].inner_html()[:300])
            break

    input("\nPress Enter to close...")
    browser.close()
```

- [ ] **Step 2: Create .env and run inspection**

```bash
cp .env.example .env
# Edit .env with real credentials before running
python inspect_site.py
```

Watch the browser open. Note down in a scratch file:
- Post-login URL (what fragment comes after `/entrar` redirect)
- How many lesson links found on the course page
- The actual CSS selectors for modules, lessons, description, comments, Panda Video iframe `src` pattern

- [ ] **Step 3: Remove inspect_site.py**

```bash
rm inspect_site.py
```

---

### Task 6: Auth Module

**Files:**
- Create: `mad_scraper/auth.py`
- Create: `tests/test_auth.py`

> Update `LOGIN_URL` and `POST_LOGIN_FRAGMENT` in `auth.py` if the post-login redirect differs from `/dashboard`.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_auth.py
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from mad_scraper import auth


def _cookie(name="session", value="abc", domain=".astronmembers.com"):
    return {"name": name, "value": value, "domain": domain,
            "path": "/", "secure": True, "expires": 9999999999}


def test_login_saves_cookies_to_file(tmp_path):
    cookies = [_cookie()]
    cookies_path = tmp_path / "cookies.json"

    mock_context = MagicMock()
    mock_context.cookies.return_value = cookies
    mock_page = MagicMock()
    mock_page.context = mock_context
    mock_browser = MagicMock()
    mock_browser.new_page.return_value = mock_page
    mock_pw = MagicMock()
    mock_pw.chromium.launch.return_value = mock_browser

    with patch("mad_scraper.auth.sync_playwright") as mock_sp:
        mock_sp.return_value.__enter__.return_value = mock_pw
        result = auth.login("user@email.com", "pass", cookies_path)

    assert cookies_path.exists()
    assert json.loads(cookies_path.read_text()) == cookies
    assert result == cookies


def test_load_cookies_reads_file(tmp_path):
    cookies = [_cookie()]
    p = tmp_path / "cookies.json"
    p.write_text(json.dumps(cookies))
    assert auth.load_cookies(p) == cookies


def test_load_cookies_raises_if_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        auth.load_cookies(tmp_path / "missing.json")


def test_cookies_to_netscape_format():
    netscape = auth.cookies_to_netscape([_cookie(name="sid", value="xyz")])
    assert "# Netscape HTTP Cookie File" in netscape
    assert ".astronmembers.com" in netscape
    assert "sid" in netscape
    assert "xyz" in netscape
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_auth.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement mad_scraper/auth.py**

```python
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

LOGIN_URL = "https://mentoriaamericandr.astronmembers.com/entrar"
POST_LOGIN_FRAGMENT = "/dashboard"  # update if redirect differs (Task 5)


def login(email: str, password: str, cookies_path: Path) -> list[dict]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
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

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_auth.py -v
```

Expected: 4 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add mad_scraper/auth.py tests/test_auth.py
git commit -m "feat: add auth module with Playwright login and cookie export"
```

---

### Task 7: Discovery Module

**Files:**
- Create: `mad_scraper/discovery.py`
- Create: `tests/test_discovery.py`

> The selectors in `_parse_lessons_html` are based on a common membership platform structure. Update them with the actual selectors found in Task 5.

- [ ] **Step 1: Write failing tests**

```python
# tests/test_discovery.py
import pytest
from mad_scraper import discovery
from mad_scraper.models import Lesson

# Representative mock HTML — update selectors in discovery.py to match real site
MOCK_HTML = """
<html><body>
<div class="course-modules">
  <div class="module">
    <h3 class="module-title">Módulo 1 - Fundamentos</h3>
    <ul>
      <li><a href="/curso/mentoria-american-dream/100/201">Aula 1 - Introdução</a></li>
      <li><a href="/curso/mentoria-american-dream/100/202">Aula 2 - Conceitos</a></li>
    </ul>
  </div>
  <div class="module">
    <h3 class="module-title">Módulo 2 - Avançado</h3>
    <ul>
      <li><a href="/curso/mentoria-american-dream/101/203">Aula 1 - Estratégia</a></li>
    </ul>
  </div>
</div>
</body></html>
"""

BASE = "https://mentoriaamericandr.astronmembers.com"


def test_parse_returns_correct_count():
    lessons = discovery._parse_lessons_html(MOCK_HTML, BASE)
    assert len(lessons) == 3


def test_parse_sets_full_url():
    lessons = discovery._parse_lessons_html(MOCK_HTML, BASE)
    assert lessons[0].url == f"{BASE}/curso/mentoria-american-dream/100/201"


def test_parse_sets_titulo():
    lessons = discovery._parse_lessons_html(MOCK_HTML, BASE)
    assert lessons[0].titulo == "Aula 1 - Introdução"


def test_parse_sets_modulo_index():
    lessons = discovery._parse_lessons_html(MOCK_HTML, BASE)
    assert lessons[0].modulo_index == 1
    assert lessons[2].modulo_index == 2


def test_parse_sets_aula_index_within_modulo():
    lessons = discovery._parse_lessons_html(MOCK_HTML, BASE)
    assert lessons[0].aula_index == 1
    assert lessons[1].aula_index == 2
    assert lessons[2].aula_index == 1


def test_parse_sets_modulo_name():
    lessons = discovery._parse_lessons_html(MOCK_HTML, BASE)
    assert "Fundamentos" in lessons[0].modulo or "Módulo 1" in lessons[0].modulo
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_discovery.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement mad_scraper/discovery.py**

```python
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from .models import Lesson
from .config import BASE_URL, COURSE_URL

# Update these selectors based on Task 5 HTML inspection
MODULE_SELECTOR = ".module, [class*='module'], [class*='section-item']"
MODULE_TITLE_SELECTOR = "h3, h2, [class*='title'], [class*='name']"
LESSON_LINK_PATTERN = "mentoria-american-dream"


def get_lessons(course_url: str, cookies: list[dict]) -> list[Lesson]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        context.add_cookies(cookies)
        page = context.new_page()
        page.goto(course_url)
        page.wait_for_load_state("networkidle")
        html = page.content()
        browser.close()
    return _parse_lessons_html(html, BASE_URL)


def _parse_lessons_html(html: str, base_url: str) -> list[Lesson]:
    soup = BeautifulSoup(html, "html.parser")
    modules = soup.select(MODULE_SELECTOR)

    if not modules:
        return _parse_flat(soup, base_url)

    lessons = []
    for modulo_index, module in enumerate(modules, 1):
        title_el = module.select_one(MODULE_TITLE_SELECTOR)
        modulo_name = title_el.get_text(strip=True) if title_el else f"Módulo {modulo_index}"
        links = module.select(f"a[href*='{LESSON_LINK_PATTERN}']")
        for aula_index, link in enumerate(links, 1):
            href = link.get("href", "")
            titulo = link.get_text(strip=True)
            if not href or not titulo:
                continue
            url = href if href.startswith("http") else f"{base_url}{href}"
            lessons.append(
                Lesson(url=url, titulo=titulo, modulo=modulo_name,
                       modulo_index=modulo_index, aula_index=aula_index)
            )
    return lessons


def _parse_flat(soup: BeautifulSoup, base_url: str) -> list[Lesson]:
    links = soup.select(f"a[href*='{LESSON_LINK_PATTERN}']")
    lessons = []
    for i, link in enumerate(links, 1):
        href = link.get("href", "")
        titulo = link.get_text(strip=True)
        if not href or not titulo:
            continue
        url = href if href.startswith("http") else f"{base_url}{href}"
        lessons.append(
            Lesson(url=url, titulo=titulo, modulo="Sem módulo",
                   modulo_index=1, aula_index=i)
        )
    return lessons
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_discovery.py -v
```

Expected: 6 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add mad_scraper/discovery.py tests/test_discovery.py
git commit -m "feat: add discovery module for course navigation"
```

---

### Task 8: Extractor Module

**Files:**
- Create: `mad_scraper/extractor.py`
- Create: `tests/test_extractor.py`

> Update selectors in `extractor.py` based on Task 5 findings (description container, comment items, Panda Video iframe `src`).

- [ ] **Step 1: Write failing tests**

```python
# tests/test_extractor.py
import pytest
from mad_scraper import extractor
from mad_scraper.models import Lesson

MOCK_HTML = """
<html><body>
  <div class="lesson-description">
    <p>Aprenda os fundamentos do copywriting americano.</p>
  </div>
  <iframe src="https://player-vz-abc123.tv.pandavideo.com.br/embed/?v=uuid-456"></iframe>
  <div class="comments">
    <div class="comment-item">
      <span class="comment-author">João Silva</span>
      <span class="comment-date">2026-01-15</span>
      <p class="comment-body">Excelente aula!</p>
    </div>
    <div class="comment-item">
      <span class="comment-author">Maria Costa</span>
      <span class="comment-date">2026-01-16</span>
      <p class="comment-body">Incrível!</p>
    </div>
  </div>
</body></html>
"""

MOCK_HTML_NO_COMMENTS = """
<html><body>
  <div class="lesson-description"><p>Só descrição aqui.</p></div>
  <iframe src="https://player-vz-abc.tv.pandavideo.com.br/embed/?v=xyz"></iframe>
</body></html>
"""


def _lesson():
    return Lesson(
        url="https://mentoriaamericandr.astronmembers.com/curso/mentoria-american-dream/1/1",
        titulo="Aula 1", modulo="Módulo 1", modulo_index=1, aula_index=1,
    )


def test_parse_returns_panda_embed_url():
    content = extractor._parse_html(MOCK_HTML, _lesson())
    assert "pandavideo" in content.panda_embed_url


def test_parse_returns_descricao():
    content = extractor._parse_html(MOCK_HTML, _lesson())
    assert "copywriting americano" in content.descricao


def test_parse_returns_comments():
    content = extractor._parse_html(MOCK_HTML, _lesson())
    assert len(content.comentarios) == 2
    assert content.comentarios[0].autor == "João Silva"
    assert content.comentarios[0].texto == "Excelente aula!"


def test_parse_returns_empty_comments_when_none():
    content = extractor._parse_html(MOCK_HTML_NO_COMMENTS, _lesson())
    assert content.comentarios == []


def test_parse_preserves_lesson_reference():
    lesson = _lesson()
    content = extractor._parse_html(MOCK_HTML, lesson)
    assert content.lesson is lesson
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_extractor.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement mad_scraper/extractor.py**

```python
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from .models import Lesson, LessonContent, Comment

# Update these selectors based on Task 5 HTML inspection
DESCRIPTION_SELECTORS = [
    ".lesson-description",
    "[class*='description']",
    "[class*='lesson-content']",
    "[class*='content-body']",
    "article",
]
COMMENT_ITEM_SELECTOR = ".comment-item, [class*='comment-item'], [class*='comment ']"
COMMENT_AUTHOR_SELECTOR = "[class*='author'], [class*='name']"
COMMENT_DATE_SELECTOR = "[class*='date'], time"
COMMENT_BODY_SELECTOR = "[class*='body'], [class*='text'], p"
PANDA_IFRAME_SELECTOR = "iframe[src*='pandavideo']"


def extract(lesson: Lesson, cookies: list[dict]) -> LessonContent:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        context.add_cookies(cookies)
        page = context.new_page()
        page.goto(lesson.url)
        page.wait_for_load_state("networkidle")
        try:
            page.wait_for_selector(PANDA_IFRAME_SELECTOR, timeout=10000)
        except Exception:
            pass
        html = page.content()
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
    for selector in DESCRIPTION_SELECTORS:
        el = soup.select_one(selector)
        if el:
            return el.get_text(strip=True)
    return ""


def _get_comments(soup: BeautifulSoup) -> list[Comment]:
    items = soup.select(COMMENT_ITEM_SELECTOR)
    comments = []
    for item in items:
        autor_el = item.select_one(COMMENT_AUTHOR_SELECTOR)
        date_el = item.select_one(COMMENT_DATE_SELECTOR)
        body_el = item.select_one(COMMENT_BODY_SELECTOR)
        autor = autor_el.get_text(strip=True) if autor_el else "Desconhecido"
        data = date_el.get_text(strip=True) if date_el else ""
        texto = body_el.get_text(strip=True) if body_el else ""
        if texto:
            comments.append(Comment(autor=autor, data=data, texto=texto))
    return comments


def _get_panda_url(soup: BeautifulSoup) -> str:
    iframe = soup.select_one(PANDA_IFRAME_SELECTOR)
    return iframe.get("src", "") if iframe else ""
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_extractor.py -v
```

Expected: 5 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add mad_scraper/extractor.py tests/test_extractor.py
git commit -m "feat: add extractor module for lesson content parsing"
```

---

### Task 9: Downloader Module

**Files:**
- Create: `mad_scraper/downloader.py`
- Create: `tests/test_downloader.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_downloader.py
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from mad_scraper import downloader

COOKIES = [{
    "name": "session", "value": "abc123", "domain": ".astronmembers.com",
    "path": "/", "secure": True, "expires": 9999999999,
}]
EMBED_URL = "https://player-vz-abc.tv.pandavideo.com.br/embed/?v=xyz"


def test_returns_true_on_success(tmp_path):
    with patch("mad_scraper.downloader.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assert downloader.download_video(EMBED_URL, tmp_path, COOKIES) is True


def test_returns_false_on_failure(tmp_path):
    with patch("mad_scraper.downloader.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        assert downloader.download_video(EMBED_URL, tmp_path, COOKIES) is False


def test_passes_embed_url_to_ytdlp(tmp_path):
    with patch("mad_scraper.downloader.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        downloader.download_video(EMBED_URL, tmp_path, COOKIES)
        cmd = mock_run.call_args[0][0]
    assert EMBED_URL in cmd


def test_passes_output_path_to_ytdlp(tmp_path):
    with patch("mad_scraper.downloader.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        downloader.download_video(EMBED_URL, tmp_path, COOKIES)
        cmd = mock_run.call_args[0][0]
    assert str(tmp_path) in " ".join(cmd)


def test_cleans_up_temp_cookie_file(tmp_path):
    with patch("mad_scraper.downloader.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        downloader.download_video(EMBED_URL, tmp_path, COOKIES)
    assert len(list(tmp_path.glob(".tmp_cookies*"))) == 0
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_downloader.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement mad_scraper/downloader.py**

```python
import subprocess
from pathlib import Path

from .auth import cookies_to_netscape


def download_video(
    panda_embed_url: str,
    lesson_dir: Path,
    cookies: list[dict],
    retries: int = 2,
) -> bool:
    cookies_file = lesson_dir / ".tmp_cookies.txt"
    cookies_file.write_text(cookies_to_netscape(cookies), encoding="utf-8")
    try:
        cmd = [
            "yt-dlp",
            "--cookies", str(cookies_file),
            "--output", str(lesson_dir / "video.%(ext)s"),
            "--retries", str(retries),
            "--no-playlist",
            "--add-header", "Referer:https://mentoriaamericandr.astronmembers.com",
            panda_embed_url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    finally:
        cookies_file.unlink(missing_ok=True)
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_downloader.py -v
```

Expected: 5 tests PASSED.

- [ ] **Step 5: Commit**

```bash
git add mad_scraper/downloader.py tests/test_downloader.py
git commit -m "feat: add downloader module wrapping yt-dlp"
```

---

### Task 10: Orchestrator and End-to-End Validation

**Files:**
- Create: `scraper.py`

- [ ] **Step 1: Run all unit tests**

```bash
pytest tests/ -v
```

Expected: all tests PASSED (progress, writer, auth, discovery, extractor, downloader).

- [ ] **Step 2: Implement scraper.py**

```python
import sys
from pathlib import Path
from dotenv import load_dotenv

from mad_scraper import auth, discovery, extractor, downloader, writer, progress
from mad_scraper.config import LOGIN_EMAIL, LOGIN_PASSWORD, OUTPUT_DIR, COOKIES_PATH, COURSE_URL
from mad_scraper.progress import Status

load_dotenv()


def run(retry_failed: bool = False) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    progress_path = OUTPUT_DIR / "progress.json"

    if not LOGIN_EMAIL or not LOGIN_PASSWORD:
        print("ERRO: LOGIN_EMAIL e LOGIN_PASSWORD não definidos no .env")
        sys.exit(1)

    print("→ Fazendo login...")
    try:
        cookies = auth.login(LOGIN_EMAIL, LOGIN_PASSWORD, COOKIES_PATH)
        print("  Login OK")
    except Exception as e:
        print(f"  FALHOU: {e}")
        sys.exit(1)

    print("→ Descobrindo aulas...")
    try:
        lessons = discovery.get_lessons(COURSE_URL, cookies)
    except Exception as e:
        print(f"  FALHOU: {e}")
        sys.exit(1)

    if retry_failed:
        failed_urls = set(progress.get_failed(progress_path))
        lessons = [l for l in lessons if l.url in failed_urls]
        print(f"  Retentando {len(lessons)} aulas com falha")
    else:
        print(f"  {len(lessons)} aulas encontradas")

    total = len(lessons)
    ok = 0
    failed = 0

    for i, lesson in enumerate(lessons, 1):
        if not retry_failed and progress.is_done(progress_path, lesson.url):
            print(f"[{i}/{total}] Pulando (concluída): {lesson.titulo}")
            ok += 1
            continue

        print(f"[{i}/{total}] {lesson.modulo} · {lesson.titulo}")

        try:
            print("  ↳ scraping...")
            content = extractor.extract(lesson, cookies)
            lesson_dir = writer.write_lesson(content, OUTPUT_DIR)

            if not content.panda_embed_url:
                print("  ↳ sem vídeo encontrado, pulando download")
                progress.mark(progress_path, lesson.url, Status.FAILED)
                failed += 1
                continue

            print("  ↳ download...")
            success = downloader.download_video(content.panda_embed_url, lesson_dir, cookies)

            if success:
                progress.mark(progress_path, lesson.url, Status.DONE)
                print("  ↳ OK")
                ok += 1
            else:
                progress.mark(progress_path, lesson.url, Status.FAILED)
                print("  ↳ FALHOU (vídeo)")
                failed += 1

        except Exception as e:
            progress.mark(progress_path, lesson.url, Status.FAILED)
            print(f"  ↳ FALHOU: {e}")
            failed += 1

    print(f"\n{'='*40}")
    print(f"Concluído: {ok}/{total} OK | {failed} falhas")
    if failed:
        print("Rode com --retry-failed para retentar as falhas")


if __name__ == "__main__":
    run(retry_failed="--retry-failed" in sys.argv)
```

- [ ] **Step 3: Dry-run with first lesson only**

Temporarily add after `print(f"[{i}/{total}]...")` the line:
```python
if i > 1: break  # DRY RUN
```

Then run:
```bash
python scraper.py
```

Expected:
- Login succeeds
- ~107 lessons found (or whatever discovery returns)
- First lesson scraped and downloaded
- Folder created: `mentoria-american-dream/modulo-01-*/aula-01-*/` with `video.mp4`, `metadata.json`, `comentarios.json`, `nota.md`

- [ ] **Step 4: Remove dry-run line and run full scrape**

Remove `if i > 1: break`, then:

```bash
python scraper.py
```

Monitor output. Expected runtime: 3–8 hours for ~107 videos. Can safely interrupt (Ctrl+C) and resume later.

To resume: `python scraper.py` (skips `done` lessons automatically)
To retry failed: `python scraper.py --retry-failed`

- [ ] **Step 5: Final commit**

```bash
git add scraper.py
git commit -m "feat: add CLI orchestrator — mad-scraper complete"
```

---

## Troubleshooting

**Login fails with timeout:** Run Task 5 again in `headless=False` mode. Check if the submit button selector differs or if there's a captcha. The actual selector may need updating in `auth.py`.

**No lessons found (0 returned):** The module/lesson selectors in `discovery.py` don't match the real HTML. Open Task 5 inspection output and update `MODULE_SELECTOR` and `LESSON_LINK_PATTERN`.

**Video download fails with 403:** Add `--add-header "Referer:https://mentoriaamericandr.astronmembers.com"` already included. If still failing, the Panda Video embed URL may need the player page URL as referer — try `page.goto()` on the embed URL directly in `inspect_site.py` and check network tab for the actual `.m3u8` URL.

**`panda_embed_url` is empty:** The iframe may load after JS execution. Add `page.wait_for_timeout(3000)` before `page.content()` in `extractor.py` as a fallback.

**Cookies expire mid-run:** Re-login by deleting `.cookies.json` and restarting. Add `auth.login(...)` call at the top of each session — it's fast (~5s).
