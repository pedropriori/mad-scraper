# MAD Scraper — Design Spec
**Data:** 2026-05-19
**Versão:** 1.0
**Status:** aprovado

---

## Contexto

Ferramenta standalone para baixar todo o conteúdo do curso "Mentoria American Dream" (plataforma astronmembers.com, vídeos no Panda Video) para uso pessoal e estudo com machine learning. ~107 aulas organizadas em módulos. O usuário tem permissão explícita do criador do conteúdo.

---

## Arquitetura

Script Python CLI com 5 fases executadas em sequência:

```
1. AUTH         Playwright faz login → salva cookies em arquivo
2. DISCOVERY    Navega índice do curso → extrai lista de módulos + URLs das ~107 aulas
3. SCRAPING     Para cada aula: extrai título, módulo, descrição, comentários, URL Panda Video
4. DOWNLOAD     yt-dlp com cookies do Playwright → baixa vídeo
5. SAVE         Grava pasta + video.mp4 + metadata.json + comentarios.json + nota.md
```

**Resumabilidade:** `progress.json` na raiz do output registra status de cada aula (`pending`, `done`, `failed`). Reruns ignoram aulas `done`. Flag `--retry-failed` retenta aulas `failed`.

**Concorrência:** sequencial (uma aula por vez) para não disparar rate limiting ou invalidação de sessão.

---

## Componentes

```
mad-scraper/
├── scraper.py          # entrypoint CLI e orquestrador
├── auth.py             # login Playwright + exportação de cookies
├── discovery.py        # navega curso, retorna lista de módulos/aulas
├── extractor.py        # extrai título, descrição, comentários de cada página
├── downloader.py       # chama yt-dlp com cookies para baixar vídeo
├── writer.py           # grava metadata.json, comentarios.json, nota.md
├── progress.py         # lê/escreve progress.json
├── config.py           # constantes, paths, leitura do .env
├── .env                # LOGIN_EMAIL, LOGIN_PASSWORD, OUTPUT_DIR
└── requirements.txt    # playwright, yt-dlp, python-dotenv
```

### Responsabilidades por módulo

| Módulo | Entrada | Saída |
|---|---|---|
| `auth.py` | credenciais do .env | arquivo `cookies.json` |
| `discovery.py` | URL do curso + cookies | `list[Lesson]` com url, título, módulo, índices |
| `extractor.py` | URL da aula + cookies | `LessonContent` com descrição, comentários, embed URL |
| `downloader.py` | embed URL Panda Video + cookies | `video.mp4` na pasta da aula |
| `writer.py` | `LessonContent` + path | `metadata.json`, `comentarios.json`, `nota.md` |
| `progress.py` | path do `progress.json` | leitura/escrita de status por aula |
| `scraper.py` | — | orquestra todos os módulos, exibe progresso |

---

## Estrutura de Output

```
mentoria-american-dream/
├── progress.json
├── modulo-01-nome-do-modulo/
│   ├── aula-01-titulo-da-aula/
│   │   ├── video.mp4
│   │   ├── metadata.json
│   │   ├── comentarios.json
│   │   └── nota.md
│   └── aula-02-titulo/
│       └── ...
└── modulo-02-nome/
    └── ...
```

### metadata.json
```json
{
  "titulo": "Nome da Aula",
  "modulo": "Nome do Módulo",
  "modulo_index": 1,
  "aula_index": 1,
  "curso": "Mentoria American Dream",
  "url": "https://mentoriaamericandr.astronmembers.com/...",
  "data_download": "2026-05-19T14:30:00",
  "duracao_segundos": 3420
}
```

### comentarios.json
```json
[
  {
    "autor": "Nome do Autor",
    "data": "2026-01-15",
    "texto": "Texto do comentário"
  }
]
```

### nota.md (Obsidian)
```markdown
---
titulo: "Nome da Aula"
modulo: "Nome do Módulo"
curso: "Mentoria American Dream"
data_download: "2026-05-19"
url: "https://..."
tags: [mentoria, american-dream, modulo-01]
---

# Nome da Aula

## Descrição
[conteúdo da descrição]

## Comentários
**Autor** · 2026-01-15
> texto do comentário
```

---

## Tratamento de Erros

| Fase | Erro | Comportamento |
|---|---|---|
| Auth | Login falhou | Para imediatamente com mensagem clara |
| Discovery | Página não carregou | Retry 3x com backoff exponencial |
| Scraping | Campo ausente (sem descrição/comentários) | Salva campo vazio, continua |
| Download | yt-dlp falhou | Retry 2x, marca `failed` no progress.json, continua |
| Save | Disco cheio / permissão | Para imediatamente |

---

## Progresso em Tempo Real

```
[23/107] Módulo 3 · Aula 5 — Estratégia de Copywriting
         ↳ scraping... OK
         ↳ download... 45% ████████░░░░░░░░░
```

---

## Dependências

```
playwright>=1.44
yt-dlp>=2024.5.0
python-dotenv>=1.0
```

Instalação adicional após `pip install playwright`: `playwright install chromium`

---

## Fora do Escopo

- Integração com CIS / LangGraph (ferramenta standalone)
- Download de múltiplos cursos simultaneamente
- Interface gráfica
- Upload ou sincronização automática com Obsidian
