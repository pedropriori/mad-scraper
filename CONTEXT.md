# MAD Scraper — Project Context

**Objetivo:** Baixar todo o conteúdo do curso "Mentoria American Dream" (~107 aulas) de astronmembers.com + Panda Video para uso pessoal e estudo com ML.

**Stack:** Python 3.11 + Playwright + BeautifulSoup4 + yt-dlp + python-dotenv + pytest

**Spec:** `docs/superpowers/specs/2026-05-19-mad-scraper-design.md`
**Plano:** `docs/superpowers/plans/2026-05-19-mad-scraper.md`

---

## Status: ✅ IMPLEMENTAÇÃO COMPLETA — 42 testes passando

| Task | Status | Commit(s) | Notas |
|------|--------|-----------|-------|
| 1: Project Setup | ✅ DONE | f188729 | requirements.txt, .env.example, dirs, git init |
| 2: Models + Config | ✅ DONE | b6e18e4 | Lesson, Comment, LessonContent, config.py |
| 3: Progress Module | ✅ DONE | 6365fb8, a0d45d3 | TDD — 8 testes. Write atômico |
| 4: Writer Module | ✅ DONE | 0fb9d83, aae7ea3 | TDD — 11 testes. Slugify, nota.md Obsidian |
| 5: HTML Inspection | ✅ DONE | 8caca95 | Seletores reais confirmados — ver seção abaixo |
| 6: Auth Module | ✅ DONE | d373093, f6b9a97 | TDD — 4 testes. Playwright login, cookies |
| 7: Discovery Module | ✅ DONE | cec8d6b, 5e4a84e | TDD — 7 testes. Sidebar com 107 aulas |
| 8: Extractor Module | ✅ DONE | 118633b, b03f7ba | TDD — 7 testes. Panda Video, comentários |
| 9: Downloader Module | ✅ DONE | 6444b9f | TDD — 5 testes. yt-dlp wrapper |
| 10: Orchestrator | ✅ DONE | b89a95e | scraper.py — CLI completo |

---

## Arquitetura

```
scraper.py              → CLI + orquestrador (login → discovery → scrape → download → save)
mad_scraper/
  models.py             → Lesson, Comment, LessonContent (dataclasses)
  config.py             → env loading, URL constants, HEADLESS flag
  progress.py           → progress.json read/write atômico (resumabilidade)
  auth.py               → Playwright login + cookie export (headless controlado por HEADLESS env)
  discovery.py          → navega curso → list[Lesson] via sidebar
  extractor.py          → navega aula → LessonContent (título, descrição, vídeo, comentários)
  downloader.py         → yt-dlp wrapper com cookie file temporário
  writer.py             → grava metadata.json, comentarios.json, nota.md (Obsidian)
tests/
  test_progress.py      → 8 testes
  test_writer.py        → 11 testes
  test_auth.py          → 4 testes
  test_discovery.py     → 7 testes
  test_extractor.py     → 7 testes
  test_downloader.py    → 5 testes
```

---

## Como Usar

```bash
# Instalar
pip install -r requirements.txt
playwright install chromium

# Configurar
cp .env.example .env
# Editar .env com LOGIN_EMAIL, LOGIN_PASSWORD, OUTPUT_DIR

# Rodar
python scraper.py

# Resumir após interrupção (Ctrl+C)
python scraper.py

# Retentar aulas com falha
python scraper.py --retry-failed
```

**Variáveis .env:**
```
LOGIN_EMAIL=kadilo1@hotmail.com
LOGIN_PASSWORD=...
OUTPUT_DIR=mentoria-american-dream
HEADLESS=false          # true para rodar sem browser visível (atenção: site pode bloquear)
```

---

## Decisões Técnicas

- **`progress.json`** usa write atômico (mkstemp + os.replace) para suportar Ctrl+C sem corromper
- **`HEADLESS=false`** por padrão — site (astronmembers.com) bloqueia headless=True na página de login
- **Discovery via sidebar**: navega para uma aula, extrai lista completa de 107 aulas da sidebar
- **Texto-only lessons** (sem Panda Video iframe): marcadas como DONE normalmente (não falha)
- **Output**: `mentoria-american-dream/modulo-XX-nome/aula-XX-nome/{video.mp4,metadata.json,comentarios.json,nota.md}`

---

## Seletores Confirmados (Task 5)

### Auth
- Email: `input[type='email']`
- Senha: `input[type='password']`
- Submit: `button[type='submit']`
- Redirect pós-login: `/dashboard`

### Discovery (sidebar da página de aula)
- Container: `.videos .accordion.scroll`
- Módulos: `dl` (filho direto do accordion)
- Título do módulo: `dl dt h3`
- Links de aula: `dl dd div.item a[href*='mentoria-american-dream']`
- Título da aula: `li.aulabox h6`
- Total: **6 módulos, 107 aulas**

### Extractor
- Título: `.videohead h6`
- Descrição: `.videodesc`
- Panda Video: `iframe.streaming-video-url[data-original-url]`
- Comentários reais: `div.comment.comment-box` com `data-id` numérico (não `{id}`)
  - Autor: `h4.name.text-truncate`
  - Data: `p.time`
  - Corpo: `p.commentdesc`

---

*Última atualização: ✅ COMPLETO — 2026-05-19*
