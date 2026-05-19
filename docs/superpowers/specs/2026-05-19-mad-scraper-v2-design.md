# MAD Scraper v2 — Design Spec
**Data:** 2026-05-19
**Versão:** 2.0
**Status:** aprovado

---

## Contexto

O MAD Scraper v1 está completo e validado em produção (42 testes, 222 Mbps, Rich UI). Esta iteração adiciona cinco melhorias ao projeto existente:

1. **Download Speed Controller** — perfis nomeados para configurar velocidade de download
2. **Interactive CLI** — menu navegável ao iniciar + dashboard ao vivo durante o scraping
3. **Anexos** — baixar arquivos anexados às aulas (PDFs, ZIPs, etc.)
4. **Browseless** — login com browser visível, scraping em background headless
5. **GitHub-ready** — README completo + estrutura para publicação

---

## Arquitetura

Dois novos arquivos + modificações cirúrgicas nos existentes. Nenhum módulo existente é reescrito.

```
scraper.py          → mantido (compatibilidade: python scraper.py ainda funciona)
cli.py              → NOVO — entry point principal com menu questionary
dashboard.py        → NOVO — rich.Live layout durante o scraping
mad_scraper/
  config.py         → + CONCURRENT_FRAGMENTS, AUTH_HEADLESS; HEADLESS default → true
  models.py         → + Attachment dataclass; + anexos em LessonContent
  downloader.py     → + progress_hooks callback; named speed profiles
  extractor.py      → + _get_attachments()
  writer.py         → + write_attachments(); + seção Anexos no nota.md
README.md           → NOVO — documentação completa do projeto
```

---

## Feature 1: Download Speed Controller

### Perfis nomeados

| Perfil | `concurrent_fragment_downloads` | Velocidade típica | Quando usar |
|--------|--------------------------------|-------------------|-------------|
| `eco` | 4 | ~20 Mbps | Conexão lenta ou compartilhada |
| `normal` | 16 | ~76 Mbps | Uso cotidiano seguro |
| `fast` | 32 | ~222 Mbps | **Padrão validado** |
| `ultra` | 64 | experimental | Conexão gigabit |

### Configuração

Via `.env`:
```
CONCURRENT_FRAGMENTS=32
```

Via flag CLI:
```
python cli.py --speed fast
```

Se `--speed` for passado, sobrescreve `CONCURRENT_FRAGMENTS`. Se nenhum for definido, usa `fast` (32).

### Onde vive

`downloader.py` define `SPEED_PROFILES: dict[str, int]` e uma função `get_fragment_count(profile: str | None) -> int` que resolve o valor final. O `config.py` expõe `CONCURRENT_FRAGMENTS`.

No menu **Configurações de download**, o usuário vê os quatro perfis com descrição e seleciona com setas — sem precisar conhecer `concurrent_fragment_downloads`.

---

## Feature 2: Interactive CLI

### Arquivo: `cli.py`

Entry point principal. Usa `questionary` para o menu. Compatibilidade: `python scraper.py` (sem args) continua funcionando como antes via `if __name__ == "__main__"` em `scraper.py`.

**Menu ao iniciar:**
```
╭───────────────────────────────────────╮
│  MAD Scraper — Mentoria American Dream │
╰───────────────────────────────────────╯

  Login: ✓ sessão ativa
  Progresso: 42/107 aulas  |  3 falhas

? O que deseja fazer?
  ▶  Iniciar scraping completo
     Retentar aulas com falha (3)
     Ver progresso atual
     Configurações de download
     Sair
```

Opções do menu:
- **Iniciar scraping completo** → chama `run(retry_failed=False)` + ativa dashboard
- **Retentar aulas com falha (N)** → chama `run(retry_failed=True)` + ativa dashboard; oculta opção se N=0
- **Ver progresso atual** → exibe tabela com status por módulo (done/failed/pending)
- **Configurações de download** → submenu com seleção de perfil de velocidade
- **Sair** → encerra

### Arquivo: `dashboard.py`

Usado pelo orquestrador durante o scraping. `rich.Live` com `Layout` em três painéis, atualizado em background thread.

```
╭── Progresso geral ──────────────────────────────────╮
│  Módulo 3 · Aula 12 — Fundamentos de Copywriting    │
│  ████████████░░░░░░  42/107  39%  ~6min restantes   │
╰─────────────────────────────────────────────────────╯
╭── Download atual ───────────────────────────────────╮
│  Fundamentos de Copywriting                          │
│  ███████████░░░░░  68%  214 Mbps  00:08 restando    │
╰─────────────────────────────────────────────────────╯
╭── Histórico (últimas 15) ───────────────────────────╮
│  ✓  Billion Swipe File                       00:25  │
│  ✓  Introdução ao Curso                      00:18  │
│  –  Grupo do WhatsApp (sem vídeo)                   │
│  ✗  Aula 07 — download falhou                       │
╰─────────────────────────────────────────────────────╯
```

**Velocidade em tempo real**: o `download_video()` recebe um callback `on_progress` opcional. O yt-dlp chama `progress_hooks` durante o download; o hook atualiza um `dict` compartilhado. O `rich.Live` (em background thread) lê esse dict a cada refresh (padrão 4 Hz).

**`DashboardState`** — dataclass compartilhada entre orquestrador e dashboard:
```python
@dataclass
class DashboardState:
    total: int
    current: int = 0
    current_title: str = ""
    phase: str = ""          # "scraping" | "download" | "skip"
    dl_pct: float = 0.0
    dl_speed_mbps: float = 0.0
    dl_eta_sec: int = 0
    history: list[HistoryEntry] = field(default_factory=list)
```

O `scraper.py` cria um `DashboardState`, passa para o `Dashboard` (que faz `.start()`) e atualiza os campos a cada iteração. O `downloader.download_video()` aceita `on_progress: Callable | None` e o chama a cada fragmento.

---

## Feature 3: Anexos

### Modelo

```python
@dataclass
class Attachment:
    nome: str
    url: str
```

`LessonContent` ganha campo `anexos: list[Attachment] = field(default_factory=list)`.

### Extração

`extractor._get_attachments(soup)` busca:
1. Qualquer elemento com texto "Anexos" ou "Arquivos" no heading (case-insensitive)
2. Links `<a href>` dentro desse contêiner com extensões: `.pdf`, `.zip`, `.docx`, `.xlsx`, `.pptx`, `.mp3`, `.csv`
3. Fallback: qualquer `<a>` dentro do contêiner de conteúdo da aula (`.videodesc` ou elemento pai) com essas extensões — nunca em elementos de navegação (sidebar, header, footer)

Se nenhum for encontrado, retorna `[]` e a execução continua normalmente.

### Download

`downloader.download_attachment(url, dest_dir, cookies)` — usa `requests` (GET autenticado com cookies) para baixar cada anexo para `aula-XX-nome/anexos/`. Retry 2x com backoff. Retorna `True/False`.

### Output

Pasta criada apenas se houver anexos:
```
aula-12-fundamentos/
  video.mp4
  metadata.json
  comentarios.json
  nota.md
  anexos/
    apostila-copywriting.pdf
    swipe-file.zip
```

`nota.md` ganha seção no final:
```markdown
## Anexos
- [apostila-copywriting.pdf](anexos/apostila-copywriting.pdf)
- [swipe-file.zip](anexos/swipe-file.zip)
```

### No orquestrador

Após `writer.write_lesson()`, se `content.anexos`, itera e chama `downloader.download_attachment()` por arquivo. Falhas de anexos marcam a aula como `done` mesmo assim (o vídeo foi baixado) — apenas logam um aviso.

---

## Feature 4: Browseless

### Comportamento padrão novo

| Fase | Antes (v1) | Depois (v2) |
|---|---|---|
| Login | headless (browser invisível) | visível — `AUTH_HEADLESS=false` |
| Discovery + Scraping | visível — `HEADLESS=false` | headless — `HEADLESS=true` |

### Config

```python
# config.py
AUTH_HEADLESS: bool = os.getenv("AUTH_HEADLESS", "false").lower() == "true"
HEADLESS: bool = os.getenv("HEADLESS", "true").lower() == "true"   # ← default muda
```

### auth.py

```python
from .config import AUTH_HEADLESS

def login(email, password, cookies_path):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=AUTH_HEADLESS)
        ...
```

O browser aparece brevemente durante o login (~5s), fecha automaticamente. Todo o restante da execução roda em background.

### .env.example atualizado

```
LOGIN_EMAIL=seu@email.com
LOGIN_PASSWORD=sua_senha
OUTPUT_DIR=mentoria-american-dream

# Velocidade de download: eco | normal | fast | ultra
CONCURRENT_FRAGMENTS=32

# Browser: false = visível, true = invisível/background
AUTH_HEADLESS=false   # browser aparece só para o login
HEADLESS=true         # scraping roda em background
```

---

## Feature 5: GitHub-ready

### README.md

Seções:
1. **Sobre** — o que é o projeto, para quê serve
2. **Pré-requisitos** — Python 3.11+, pip, chromium
3. **Instalação** — clone, pip install, playwright install chromium
4. **Configuração** — tabela de todas as variáveis do `.env` com valores padrão e descrição
5. **Uso** — todos os comandos com exemplos
6. **Perfis de velocidade** — tabela dos quatro perfis
7. **Estrutura de output** — árvore de pastas
8. **Troubleshooting** — login falha, discovery retorna 0, download 403, cookies expiram
9. **Testes** — como rodar

### .gitignore

Verificar que cobre (e adicionar se faltando):
- `.env`
- `.cookies.json`
- `mentoria-american-dream/` (output dir)
- `__pycache__/`, `.pytest_cache/`
- `*.mp4`, `*.ts`

Sem `LICENSE` — projeto pessoal; pode ser adicionada depois se publicar.

---

## Tratamento de Erros

| Feature | Erro | Comportamento |
|---|---|---|
| Speed controller | Perfil desconhecido passado via `--speed` | Aviso + usa `fast` como fallback |
| Dashboard | yt-dlp não chama progress_hooks | Download continua, velocidade exibe `—` |
| Anexos | Seção não encontrada | `[]`, continua normalmente |
| Anexos | Download de arquivo falhou | Log aviso, aula marcada `done` mesmo assim |
| Browseless | Login falha (captcha) | Mensagem clara + saída; usuário pode setar `AUTH_HEADLESS=false` |

---

## Dependências adicionais

```
questionary>=2.0     # menu interativo
requests>=2.31       # download de anexos
```

`rich` já está nas dependências (usado no v1).

---

## Fora do escopo

- Integração com CIS / LangGraph
- Download paralelo de múltiplas aulas simultaneamente
- Interface gráfica
- Upload automático para Obsidian
- Suporte a outros cursos além de MAD
