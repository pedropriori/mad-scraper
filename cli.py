#!/usr/bin/env python3
"""MAD Scraper — interactive CLI. Run: python cli.py"""
import sys
import io
from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from mad_scraper.config import OUTPUT_DIR, CONCURRENT_FRAGMENTS
from mad_scraper.downloader import SPEED_PROFILES
from mad_scraper import progress as _progress
from mad_scraper.progress import Status

if getattr(sys.stdout, 'encoding', '').lower() not in ('utf-8', 'utf_8'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

console = Console(highlight=False)

_PROGRESS_PATH = OUTPUT_DIR / "progress.json"


def _status_summary() -> dict:
    """Return dict with keys: done, failed, total — derived from progress.load()."""
    data = _progress.load(_PROGRESS_PATH)
    done = sum(1 for s in data.values() if s == Status.DONE.value)
    failed = sum(1 for s in data.values() if s == Status.FAILED.value)
    total = len(data)
    return {"done": done, "failed": failed, "total": total}


def _show_progress_table() -> None:
    """Display a Rich table summarising every recorded lesson and its status."""
    data = _progress.load(_PROGRESS_PATH)
    if not data:
        console.print("[dim]Nenhum progresso registrado ainda.[/dim]\n")
        return

    table = Table(title="Progresso das aulas", show_lines=False)
    table.add_column("Status", style="bold", width=10)
    table.add_column("URL", overflow="fold")

    status_style = {
        Status.DONE.value: "[green]done[/green]",
        Status.FAILED.value: "[red]failed[/red]",
        Status.PENDING.value: "[yellow]pending[/yellow]",
    }

    for url, status in data.items():
        styled = status_style.get(status, status)
        table.add_row(styled, url)

    console.print(table)
    console.print()


def _choose_speed() -> str | None:
    choices = [
        questionary.Choice(
            "eco    —  4 fragmentos  (~20 Mbps)   Conexao lenta ou compartilhada",
            value="eco"
        ),
        questionary.Choice(
            "normal — 16 fragmentos  (~76 Mbps)   Uso cotidiano seguro",
            value="normal"
        ),
        questionary.Choice(
            "fast   — 32 fragmentos  (~222 Mbps)  Padrao validado  *",
            value="fast"
        ),
        questionary.Choice(
            "ultra  — 64 fragmentos  (exp.)       Conexao gigabit+",
            value="ultra"
        ),
        questionary.Choice("<- Voltar", value=None),
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
        login_str = "[green]v sessao salva[/green]" if login_ok else "[yellow]! nao logado[/yellow]"
        console.print(f"  Login: {login_str}")
        console.print(
            f"  Progresso: [green]{summary['done']} concluidas[/green]  "
            f"[red]{summary['failed']} falhas[/red]  "
            f"[dim]{summary['total']} registradas[/dim]"
        )
        active_frags = SPEED_PROFILES.get(speed_profile, CONCURRENT_FRAGMENTS) if speed_profile else CONCURRENT_FRAGMENTS
        console.print(
            f"  Velocidade: [cyan]{speed_profile or 'padrao'}[/cyan] "
            f"[dim]({active_frags} fragmentos)[/dim]"
        )
        console.print()

        choices = [
            questionary.Choice("  Iniciar scraping completo", value="run"),
        ]
        if summary["failed"] > 0:
            choices.append(questionary.Choice(
                f"  Retentar aulas com falha ({summary['failed']})", value="retry"
            ))
        if summary["done"] > 0:
            choices.append(questionary.Choice(
                f"  Baixar anexos faltantes ({summary['done']} aulas)", value="anexos"
            ))
        choices += [
            questionary.Choice("  Ver progresso atual", value="progress"),
            questionary.Choice("  Configuracoes de download", value="speed"),
            questionary.Choice("  Sair", value="exit"),
        ]

        action = questionary.select("O que deseja fazer?", choices=choices).ask()

        if action is None or action == "exit":
            console.print("[dim]Ate mais.[/dim]")
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
        elif action == "anexos":
            console.print()
            from scraper import run_anexos_only
            run_anexos_only(speed_profile=speed_profile)
            break
        elif action == "progress":
            console.print()
            _show_progress_table()
        elif action == "speed":
            console.print()
            chosen = _choose_speed()
            if chosen:
                speed_profile = chosen
                console.print(f"[green]v[/green] Perfil alterado para [cyan]{chosen}[/cyan]\n")


if __name__ == "__main__":
    main()
