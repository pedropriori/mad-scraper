# MAD Scraper — Project Context

**Objetivo:** Baixar todo o conteúdo do curso "Mentoria American Dream" (~107 aulas) de astronmembers.com + Panda Video para uso pessoal e estudo com ML.

**Stack:** Python 3.11 + Playwright + BeautifulSoup4 + yt-dlp + python-dotenv + pytest

**Spec:** `docs/superpowers/specs/2026-05-19-mad-scraper-design.md`
**Plano:** `docs/superpowers/plans/2026-05-19-mad-scraper.md`

---

## Arquitetura

```
scraper.py          → CLI + orquestrador
mad_scraper/
  models.py         → Lesson, Comment, LessonContent (dataclasses)
  config.py         → env loading, URL constants
  progress.py       → progress.json read/write (resumabilidade)
  auth.py           → Playwright login + cookie export
  discovery.py      → navega curso → list[Lesson]
  extractor.py      → navega aula → LessonContent
  downloader.py     → yt-dlp wrapper
  writer.py         → grava metadata.json, comentarios.json, nota.md
tests/
  test_progress.py
  test_writer.py
  test_auth.py
  test_discovery.py
  test_extractor.py
  test_downloader.py
```

---

## Status das Tasks

| Task | Status | Commit(s) | Notas |
|------|--------|-----------|-------|
| 1: Project Setup | ✅ DONE | f188729 | requirements.txt, .env.example, dirs, git init |
| 2: Models + Config | ✅ DONE | b6e18e4 | Lesson, Comment, LessonContent, config.py |
| 3: Progress Module | ✅ DONE | 6365fb8, a0d45d3 | TDD — 8 testes. Fix de write atômico adicionado |
| 4: Writer Module | ✅ DONE | 0fb9d83, aae7ea3 | TDD — 11 testes. Fixes: slugify, trailing newline, multiline comments, constant |
| 5: HTML Inspection | ⏳ PENDING | — | **MANUAL** — requer senha do usuário |
| 6: Auth Module | ⏳ PENDING | — | Depende de selectors do Task 5 |
| 7: Discovery Module | ⏳ PENDING | — | Depende de selectors do Task 5 |
| 8: Extractor Module | ⏳ PENDING | — | Depende de selectors do Task 5 |
| 9: Downloader Module | ⏳ PENDING | — | |
| 10: Orchestrator | ⏳ PENDING | — | scraper.py — dry-run + full run |

---

## Decisões Técnicas Relevantes

- **Playwright retorna HTML renderizado** → BeautifulSoup faz o parsing (funções puras, testáveis sem browser)
- **`progress.json`** usa write atômico (mkstemp + os.replace) para suportar Ctrl+C sem corromper arquivo
- **TDD**: cada módulo tem testes antes da implementação
- **Seletores CSS** das Tasks 6-8 são estimativas — **DEVEM ser ajustados após Task 5**
- **Output**: `mentoria-american-dream/modulo-XX-nome/aula-XX-nome/{video.mp4,metadata.json,comentarios.json,nota.md}`

---

## Task 5 — Atenção Especial (Manual)

Antes de implementar auth.py, discovery.py, extractor.py, é necessário rodar `inspect_site.py` com credenciais reais para descobrir os CSS selectors corretos. O plano inclui o script completo.

**Credenciais necessárias:**
- LOGIN_EMAIL: kadilo1@hotmail.com (já configurado)
- LOGIN_PASSWORD: **requer input do usuário**

---

## Como Usar (quando completo)

```bash
# Instalar
pip install -r requirements.txt
playwright install chromium

# Configurar
cp .env.example .env
# editar .env com credenciais

# Rodar
python scraper.py

# Resumir após interrupção
python scraper.py

# Retentar falhas
python scraper.py --retry-failed
```

---

*Última atualização: Task 4 concluída — 2026-05-19*
