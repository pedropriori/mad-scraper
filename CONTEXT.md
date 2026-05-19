# MAD Scraper — Project Context

**Objetivo:** Baixar todo o conteúdo do curso "Mentoria American Dream" (~107 aulas) de astronmembers.com + Panda Video para uso pessoal e estudo com ML.

**Stack:** Python 3.11 + Playwright + BeautifulSoup4 + yt-dlp + python-dotenv + rich + pytest

**Spec:** `docs/superpowers/specs/2026-05-19-mad-scraper-design.md`
**Plano:** `docs/superpowers/plans/2026-05-19-mad-scraper.md`

---

## Status: ✅ COMPLETO E VALIDADO EM PRODUÇÃO

| Task | Status | Commit(s) | Notas |
|------|--------|-----------|-------|
| 1: Project Setup | ✅ DONE | f188729 | requirements.txt, .env.example, dirs, git init |
| 2: Models + Config | ✅ DONE | b6e18e4 | Lesson, Comment, LessonContent, config.py |
| 3: Progress Module | ✅ DONE | 6365fb8, a0d45d3 | TDD — 8 testes. Write atômico |
| 4: Writer Module | ✅ DONE | 0fb9d83, aae7ea3 | TDD — 11 testes. Slugify, nota.md Obsidian |
| 5: HTML Inspection | ✅ DONE | 8caca95 | Seletores reais confirmados |
| 6: Auth Module | ✅ DONE | d373093, f6b9a97 | TDD — 4 testes. Playwright login, cookies |
| 7: Discovery Module | ✅ DONE | cec8d6b, 5e4a84e | TDD — 7 testes. Sidebar com 107 aulas |
| 8: Extractor Module | ✅ DONE | 118633b, b03f7ba | TDD — 7 testes. Panda Video, comentários |
| 9: Downloader Module | ✅ DONE | 6444b9f | TDD — 5 testes. yt-dlp wrapper |
| 10: Orchestrator | ✅ DONE | b89a95e | scraper.py — CLI completo |
| 11: Dry-run + Bugs | ✅ DONE | 0118c44 | Discovery fix, stdout encoding fix |
| 12: Performance + UI | ✅ DONE | 452f030, 797d7f5, fb1430e | Rich UI, browser compartilhado, 222 Mbps |

**Testes:** 42 passando (8 progress + 11 writer + 4 auth + 7 discovery + 7 extractor + 5 downloader)

---

## Arquitetura

```
scraper.py              → CLI + orquestrador (1 browser session para tudo)
mad_scraper/
  models.py             → Lesson, Comment, LessonContent (dataclasses)
  config.py             → env loading, URL constants, HEADLESS flag
  progress.py           → progress.json read/write atômico (resumabilidade)
  auth.py               → Playwright login + cookie export
  discovery.py          → get_lessons_with_page() + get_lessons() (tests)
  extractor.py          → extract_with_page() + extract() (tests)
  downloader.py         → yt-dlp Python API, 32 fragmentos paralelos
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

# Rodar (baixa tudo do zero, pula aulas já concluídas)
python scraper.py

# Retentar aulas com falha
python scraper.py --retry-failed
```

**Variáveis .env:**
```
LOGIN_EMAIL=kadilo1@hotmail.com
LOGIN_PASSWORD=...
OUTPUT_DIR=mentoria-american-dream
HEADLESS=false          # true para rodar sem browser visível
```

**Output por aula:**
```
mentoria-american-dream/
  modulo-01-nome/
    aula-01-nome/
      video.mp4
      metadata.json
      comentarios.json
      nota.md
  progress.json          ← resumabilidade (atomic write)
```

---

## Decisões Técnicas

### Sessão de Browser Compartilhada
`scraper.py` abre **um único browser** após o login e reutiliza o mesmo `page` para discovery + todas as 107 aulas. Antes, `extract()` abria um browser por aula — 107 launches, extremamente lento.

### Captura de URL do Vídeo (m3u8 via network interception)
O Panda Video player faz dois requests m3u8 distintos:
- `playlist.m3u8?get_qualities=1` → **vídeo de erro de 6s** (deve ser ignorado)
- `1080p/video.m3u8` → **stream real** (qualidade 1080p, até 3,5 GB)

`extract_with_page()` intercepta requests de rede via `page.on("request", ...)` e filtra para capturar apenas `/{quality}/video.m3u8`, preferindo 1080p > 720p > 480p > 360p. O `data-original-url` do iframe é apenas a embed URL do player — não funciona diretamente com yt-dlp.

### Download Paralelo de Fragmentos HLS
Panda Video serve vídeos via HLS (`.ts` segments no `cdn.pandavideo.com`). Benchmarks:

| `concurrent_fragment_downloads` | Velocidade | Tempo (708 MB) |
|---|---|---|
| 1 (padrão yt-dlp) | ~5 Mbps | ~20+ minutos |
| 16 | 76 Mbps | 74s |
| **32** (atual) | **222 Mbps** | **25s** |

### yt-dlp via Python API
O binário `yt-dlp` não está no PATH do Windows — usa-se `yt_dlp.YoutubeDL` diretamente, sem subprocess.

### Bugs Encontrados e Corrigidos no Dry-Run
- **`COURSE_URL` redireciona para `/dashboard`**: discovery navega para qualquer link `a[href*='mentoria-american-dream']` encontrado na página atual em vez de clicar em `dl.modulo-container dt`
- **Stdout cp1252 no Windows**: `sys.stdout` wrapped com `io.TextIOWrapper(encoding='utf-8')` antes de qualquer print Unicode
- **`?get_qualities=1` retorna vídeo de erro**: filtrado no interceptor de requests

---

## Seletores Confirmados

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
- Total: **6 módulos, 107 aulas**

### Extractor
- Título: `.videohead h6`
- Descrição: `.videodesc`
- Panda Video iframe: `iframe.streaming-video-url[data-original-url]`
- m3u8 real: capturado via `page.on("request")`, padrão `/{quality}/video.m3u8`
- Comentários reais: `div.comment.comment-box` com `data-id` numérico (não `{id}`)
  - Autor: `h4.name.text-truncate`
  - Data: `p.time`
  - Corpo: `p.commentdesc`

---

## UI (rich)

```
╭───────────────────────────────────────╮
│ MAD Scraper — Mentoria American Dream │
╰───────────────────────────────────────╯

✓ Login concluído
✓ 107 aulas descobertas

⠋ download  [42/107] Fundamentos do Copywriting ━━━━━━━━  42/107  0:04:12  0:05:30

  – [1/107] Grupo de Whatsapp do CF (sem vídeo)
  ✓ [2/107] Billion Swipe File
  ✓ [3/107] Sorteio Macbook + Tira dúvidas
  ...
```

---

*Última atualização: ✅ PRODUÇÃO VALIDADA — 2026-05-19*
