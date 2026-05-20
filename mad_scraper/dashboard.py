from dataclasses import dataclass, field
from typing import Optional

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table


@dataclass
class HistoryEntry:
    index: int
    titulo: str
    status: str   # "done" | "skip" | "failed"
    duration_sec: int = 0


@dataclass
class DashboardState:
    total: int
    current: int = 0
    current_titulo: str = ""
    current_modulo: str = ""
    phase: str = "aguardando"   # "scraping" | "download" | "anexos" | "skip" | "aguardando"
    dl_pct: float = 0.0
    dl_speed_mbps: float = 0.0
    dl_eta_sec: int = 0
    history: list[HistoryEntry] = field(default_factory=list)

    def add_history(self, entry: HistoryEntry) -> None:
        self.history.append(entry)
        if len(self.history) > 15:
            self.history = self.history[-15:]


class Dashboard:
    def __init__(self, state: DashboardState, console: Optional[Console] = None):
        self._state = state
        self._console = console or Console(highlight=False)
        self._live: Optional[Live] = None

    def __enter__(self) -> "Dashboard":
        self._live = Live(
            self._render(),
            console=self._console,
            refresh_per_second=4,
        )
        self._live.__enter__()
        return self

    def __exit__(self, *args) -> None:
        if self._live:
            self._live.__exit__(*args)
            self._live = None

    def refresh(self) -> None:
        if self._live:
            self._live.update(self._render())

    def _render(self) -> Group:
        s = self._state

        # Panel 1: Overall progress
        pct = (s.current / s.total * 100) if s.total else 0
        bar_filled = int(pct / 5)
        bar = "█" * bar_filled + "░" * (20 - bar_filled)
        status_line = (
            f"[bold]{s.current_modulo}[/bold]  ·  {s.current_titulo}"
            if s.current_titulo
            else "[dim]Aguardando...[/dim]"
        )
        progress_panel = Panel(
            f"{status_line}\n  {bar}  {s.current}/{s.total}  {pct:.0f}%",
            title="[bold blue]MAD Scraper — Progresso geral[/bold blue]",
        )

        # Panel 2: Current download
        if s.phase == "download" and s.dl_pct > 0:
            dl_filled = int(s.dl_pct / 5)
            dl_bar = "█" * dl_filled + "░" * (20 - dl_filled)
            speed_str = f"  {s.dl_speed_mbps:.0f} Mbps" if s.dl_speed_mbps else ""
            eta_str = f"  {s.dl_eta_sec}s restando" if s.dl_eta_sec else ""
            dl_body = f"  {dl_bar}  {s.dl_pct:.0f}%{speed_str}{eta_str}"
        else:
            dl_body = f"  [dim]{s.phase}...[/dim]"
        download_panel = Panel(
            f"  [bold]{s.current_titulo or '—'}[/bold]\n{dl_body}",
            title="[bold]Download atual[/bold]",
        )

        # Panel 3: History table
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("", width=2)
        table.add_column("Aula", no_wrap=True, max_width=55)
        table.add_column("", justify="right", width=6)
        _icons = {
            "done": ("✓", "green"),
            "skip": ("–", "dim"),
            "failed": ("✗", "red"),
        }
        for entry in reversed(s.history):
            icon, style = _icons.get(entry.status, ("?", "white"))
            dur = f"{entry.duration_sec}s" if entry.duration_sec else ""
            table.add_row(
                f"[{style}]{icon}[/{style}]",
                f"[{style}]{entry.titulo[:55]}[/{style}]",
                f"[dim]{dur}[/dim]",
            )
        history_panel = Panel(table, title="[bold]Histórico[/bold]")

        return Group(progress_panel, download_panel, history_panel)
