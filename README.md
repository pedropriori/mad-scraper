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

62 testes cobrindo progress, writer, auth, discovery, extractor, downloader, dashboard.

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
