import sys
import io
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    Progress, SpinnerColumn, BarColumn, TextColumn,
    MofNCompleteColumn, TimeElapsedColumn, TimeRemainingColumn,
)

from mad_scraper import auth, discovery, extractor, downloader, writer, progress
from mad_scraper.config import LOGIN_EMAIL, LOGIN_PASSWORD, OUTPUT_DIR, COOKIES_PATH, COURSE_URL, HEADLESS
from mad_scraper.progress import Status

load_dotenv()
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

console = Console(highlight=False)


def run(retry_failed: bool = False) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    progress_path = OUTPUT_DIR / "progress.json"

    if not LOGIN_EMAIL or not LOGIN_PASSWORD:
        console.print("[red]✗ ERRO:[/red] LOGIN_EMAIL e LOGIN_PASSWORD não definidos no .env")
        sys.exit(1)

    console.print(Panel.fit("[bold]MAD Scraper[/bold] — Mentoria American Dream", style="bold blue"))
    console.print()

    # ── Login ──────────────────────────────────────────────────────────────
    with console.status("[cyan]Fazendo login...[/cyan]"):
        try:
            cookies = auth.login(LOGIN_EMAIL, LOGIN_PASSWORD, COOKIES_PATH)
        except Exception as e:
            console.print(f"[red]✗ Login FALHOU:[/red] {e}")
            sys.exit(1)
    console.print("[green]✓[/green] Login concluído")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        try:
            ctx = browser.new_context()
            ctx.add_cookies(cookies)
            page = ctx.new_page()

            # ── Discovery ──────────────────────────────────────────────────
            with console.status("[cyan]Descobrindo aulas...[/cyan]"):
                try:
                    lessons = discovery.get_lessons_with_page(COURSE_URL, page)
                except Exception as e:
                    console.print(f"[red]✗ Discovery FALHOU:[/red] {e}")
                    sys.exit(1)

            if retry_failed:
                failed_urls = set(progress.get_failed(progress_path))
                lessons = [l for l in lessons if l.url in failed_urls]
                console.print(f"[yellow]↻[/yellow] {len(lessons)} aulas com falha para retentar")
            else:
                console.print(f"[green]✓[/green] {len(lessons)} aulas descobertas")

            console.print()
            total = len(lessons)
            ok = 0
            failed = 0

            # ── Scraping loop ──────────────────────────────────────────────
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(bar_width=28),
                MofNCompleteColumn(),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                console=console,
                expand=True,
            ) as prog:
                task = prog.add_task("iniciando...", total=total)

                for i, lesson in enumerate(lessons, 1):
                    label = f"[{i}/{total}] {lesson.titulo[:55]}"

                    if not retry_failed and progress.is_done(progress_path, lesson.url):
                        prog.advance(task)
                        ok += 1
                        continue

                    prog.update(task, description=f"scraping  {label}")

                    try:
                        content = extractor.extract_with_page(lesson, page)
                        lesson_dir = writer.write_lesson(content, OUTPUT_DIR)

                        if not content.panda_embed_url:
                            progress.mark(progress_path, lesson.url, Status.DONE)
                            console.print(f"  [dim]–[/dim] {label} [dim](sem vídeo)[/dim]")
                            prog.advance(task)
                            ok += 1
                            continue

                        prog.update(task, description=f"download  {label}")
                        success = downloader.download_video(content.panda_embed_url, lesson_dir, cookies)

                        if success:
                            progress.mark(progress_path, lesson.url, Status.DONE)
                            console.print(f"  [green]✓[/green] {label}")
                            ok += 1
                        else:
                            progress.mark(progress_path, lesson.url, Status.FAILED)
                            console.print(f"  [red]✗[/red] {label} [dim](download falhou)[/dim]")
                            failed += 1

                    except Exception as e:
                        progress.mark(progress_path, lesson.url, Status.FAILED)
                        console.print(f"  [red]✗[/red] {label} [red]{e}[/red]")
                        failed += 1

                    prog.advance(task)

        finally:
            browser.close()

    console.print()
    console.rule()
    if failed:
        console.print(f"[bold]Concluído:[/bold] {ok}/{total} OK  [red]{failed} falhas[/red]")
        console.print("[yellow]Rode com --retry-failed para retentar as falhas[/yellow]")
    else:
        console.print(f"[bold green]Concluído:[/bold green] {ok}/{total} OK — tudo certo!")


if __name__ == "__main__":
    run(retry_failed="--retry-failed" in sys.argv)
