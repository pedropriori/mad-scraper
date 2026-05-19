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
| 5: HTML Inspection | ✅ DONE | 8caca95 | Seletores reais descobertos — ver seção abaixo |
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

## Seletores Reais (Task 5 — Concluída)

### Auth
- Email input: `input[type='email']`
- Password input: `input[type='password']`
- Submit: `button[type='submit']`
- Post-login fragment: `/dashboard`

### Discovery
- **Estratégia**: Navegar para qualquer URL de aula (ex: `{COURSE_URL}/125393/707026`) → sidebar carrega 107 aulas
- Sidebar container: `.videos .accordion.scroll`
- Módulos na sidebar: `dl` (direto dentro do accordion — NÃO `dl.modulo-container`)
- Título do módulo: `dl dt h3`
- Links de aula: `dl dd div.item a[href*='mentoria-american-dream']`
- Título da aula: `a li.aulabox h6` (ou `li h6` dentro do `a`)
- URL completa: `BASE_URL + "/" + href.lstrip("/")`
- Total: **6 módulos, 107 aulas**

### Extractor (página de cada aula)
- Título: `.videohead h6`
- Descrição: `.videodesc`
- Panda Video URL: `iframe.streaming-video-url` → atributo `data-original-url`
  - (ou `iframe[data-streaming-video]`)
- Comentários reais: `div.comment.comment-box[data-id]:not([data-id="{id}"])`
  - Autor: `h4.name.text-truncate`
  - Data: `p.time`
  - Corpo: `p.commentdesc`
- Sem comentários: elemento `.nocomments` presente com "Seja o primeiro a comentar"

### Estrutura da sidebar (módulo/aula)
```html
<dl>
  <dt><div class="head"><div class="content"><h3>Módulo X</h3></div></div></dt>
  <dd>
    <div class="item"><a href="curso/mentoria-american-dream/125393/LESSON_ID">
      <li class="aulabox" data-aulaid="LESSON_ID">
        <div class="item-titulo"><h6>Título da Aula</h6></div>
      </li>
    </a></div>
  </dd>
</dl>
```

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

*Última atualização: Task 5 concluída — 2026-05-19*
