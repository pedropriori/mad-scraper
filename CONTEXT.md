# MAD Scraper — Project Context

**Objetivo:** Baixar todo o conteúdo do curso "Mentoria American Dream" (~107 aulas) de astronmembers.com + Panda Video para uso pessoal e estudo com ML.

**Stack:** Python 3.11 + Playwright + BeautifulSoup4 + yt-dlp + python-dotenv + rich + questionary + requests + pytest

**Spec:** `docs/superpowers/specs/2026-05-19-mad-scraper-design.md`
**Plano v1:** `docs/superpowers/plans/2026-05-19-mad-scraper.md`
**Plano v2:** `docs/superpowers/plans/2026-05-19-mad-scraper-v2.md`

---

## Status: ✅ v1 COMPLETO | ✅ v2 COMPLETO

### v1 — Concluído e validado em produção

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

### v2 — Em execução (subagent-driven-development)

| Task | Status | Commit | Testes | Notas |
|------|--------|--------|--------|-------|
| 1: Instalar questionary + requests | ✅ DONE | a8d56f0 | 42→42 | questionary 2.1.1, requests 2.32.5 |
| 2: Config AUTH_HEADLESS, CONCURRENT_FRAGMENTS | ✅ DONE | 6ecfd0b | 42→43 | HEADLESS default → true |
| 3: Models — Attachment dataclass | ✅ DONE | 6a5222c | 43→45 | Attachment + LessonContent.anexos |
| 4: Downloader — speed profiles + download_attachment | ✅ DONE | ccff265 | 45→51 | SPEED_PROFILES, get_fragment_count, on_progress |
| 5: Extractor — _get_attachments | ✅ DONE | d66a038 | 51→54 | _collect_file_links, fallback logic |
| 6: Writer — Anexos section in nota.md | ✅ DONE | c5331c4 | 54→57 | ## Anexos com links relativos |
| 7: Dashboard — rich.Live 3 painéis | ✅ DONE | ba38a44 | 57→62 | DashboardState, HistoryEntry, Dashboard |
| 8: Orchestrator — scraper.py atualizado | ✅ DONE | bd69557 | 62→62 | Dashboard + on_progress + anexos |
| 9: CLI interativa | ✅ DONE | e493e48 | 62→62 | questionary menu, progress integration |
| 10: README + .gitignore | ✅ DONE | 680e47e | 62→62 | docs completos, gitignore atualizado |

**Testes: 62 passando — v2 COMPLETO**

---

## Arquitetura

```
cli.py                  → NOVO: entry point interativo (questionary menu)
scraper.py              → atualizado: Dashboard, on_progress, anexos
mad_scraper/
  models.py             → Lesson, Comment, LessonContent, Attachment (v2)
  config.py             → env loading, AUTH_HEADLESS, HEADLESS, CONCURRENT_FRAGMENTS (v2)
  progress.py           → progress.json read/write atômico (resumabilidade)
  auth.py               → Playwright login, usa AUTH_HEADLESS (v2)
  discovery.py          → get_lessons_with_page() + get_lessons() (tests)
  extractor.py          → extract_with_page() + _get_attachments() (v2)
  downloader.py         → SPEED_PROFILES, download_video(), download_attachment() (v2)
  writer.py             → grava metadata.json, comentarios.json, nota.md + Anexos (v2)
  dashboard.py          → NOVO: DashboardState, HistoryEntry, Dashboard (rich.Live)
tests/
  test_progress.py      → 8 testes
  test_writer.py        → 16 testes (+ 5 novos v2)
  test_auth.py          → 5 testes (+ 1 novo v2)
  test_discovery.py     → 7 testes
  test_extractor.py     → 10 testes (+ 3 novos v2)
  test_downloader.py    → 11 testes (+ 6 novos v2)
  test_dashboard.py     → 5 testes (NOVO v2)
```

---

## Como Usar

### v2 (CLI interativa — recomendado)
```bash
python cli.py
```
Menu com setas:
- Iniciar scraping completo
- Retentar aulas com falha
- Ver progresso atual
- Configurações de download (perfis eco/normal/fast/ultra)
- Sair

### Linha de Comando Direta
```bash
# Scraping completo
python scraper.py

# Retentar falhas
python scraper.py --retry-failed

# Perfil de velocidade
python scraper.py --speed normal
```

### Configurar
```bash
cp .env.example .env
# Editar .env com LOGIN_EMAIL, LOGIN_PASSWORD
```

**Variáveis .env:**
```
LOGIN_EMAIL=...
LOGIN_PASSWORD=...
OUTPUT_DIR=mentoria-american-dream
AUTH_HEADLESS=false   # false = browser visível no login (default)
HEADLESS=true         # true = scraping em background (default v2)
CONCURRENT_FRAGMENTS=32  # fragmentos HLS paralelos
```

**Output por aula:**
```
mentoria-american-dream/
  modulo-01-nome/
    aula-01-nome/
      video.mp4
      metadata.json
      comentarios.json
      nota.md          ← Obsidian + seção ## Anexos (v2)
      anexos/          ← criado só se houver arquivos (v2)
        apostila.pdf
  progress.json        ← resumabilidade (atomic write)
```

---

## Perfis de Velocidade (v2)

| Perfil | Fragmentos | Velocidade típica |
|--------|-----------|-------------------|
| eco | 4 | ~20 Mbps |
| normal | 16 | ~76 Mbps |
| **fast** | **32** | **~222 Mbps (padrão validado)** |
| ultra | 64 | experimental |

---

## Decisões Técnicas

### Sessão de Browser Compartilhada
`scraper.py` abre **um único browser** após o login e reutiliza o mesmo `page` para discovery + todas as 107 aulas.

### Captura de URL do Vídeo (m3u8 via network interception)
O Panda Video player faz dois requests m3u8 distintos:
- `playlist.m3u8?get_qualities=1` → **vídeo de erro de 6s** (deve ser ignorado)
- `1080p/video.m3u8` → **stream real** (qualidade 1080p, até 3,5 GB)

`extract_with_page()` intercepta requests via `page.on("request", ...)` e filtra para `/{quality}/video.m3u8`.

### Download Paralelo de Fragmentos HLS (v2: configurável)
| `concurrent_fragment_downloads` | Velocidade | Tempo (708 MB) |
|---|---|---|
| 1 (padrão yt-dlp) | ~5 Mbps | ~20+ minutos |
| 16 | 76 Mbps | 74s |
| **32** (padrão v2) | **222 Mbps** | **25s** |

### AUTH_HEADLESS vs HEADLESS (v2)
- `AUTH_HEADLESS=false` (padrão): browser **visível** durante o login (~5s) para captcha/2FA
- `HEADLESS=true` (padrão): scraping inteiro roda **em background**

### yt-dlp via Python API
O binário `yt-dlp` não está no PATH do Windows — usa-se `yt_dlp.YoutubeDL` diretamente.

### Bugs Encontrados e Corrigidos no Dry-Run (v1)
- **`COURSE_URL` redireciona para `/dashboard`**: discovery navega para qualquer link `a[href*='mentoria-american-dream']`
- **Stdout cp1252 no Windows**: `sys.stdout` wrapped com `io.TextIOWrapper(encoding='utf-8')`
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

### Extractor — Anexos (v2)
- Seção detectada por heading com "anexo" ou "arquivo" no texto
- Links coletados com extensões: `.pdf`, `.zip`, `.docx`, `.xlsx`, `.pptx`, `.mp3`, `.csv`
- Fallback: busca dentro do parent de `.videodesc`

---

### v2 — Adições pós-conclusão

| Feature | Commit | Testes | Notas |
|---------|--------|--------|-------|
| `--anexos-only`: baixar anexos faltantes | dd2e386 | 62→63 | `get_done()`, `run_anexos_only()`, menu CLI |

**Testes: 63 passando**

---

## Modo Anexos Faltantes

Baixa apenas os arquivos de aulas já concluídas, sem re-baixar vídeos.

```bash
# Via CLI (recomendado)
python cli.py
# → "Baixar anexos faltantes (N aulas)"

# Via linha de comando
python scraper.py --anexos-only
python scraper.py --anexos-only --speed normal
```

**Como funciona:**
1. Lê `progress.json` → pega URLs com status `done`
2. Faz login + discovery → filtra para as aulas concluídas
3. Para cada aula: extrai anexos da página, verifica se arquivo já existe em `anexos/`
4. Baixa apenas os arquivos ausentes — não toca nos vídeos

---

*Última atualização: ✅ v2 COMPLETO + modo anexos-only — 63 testes passando — 2026-05-19*
