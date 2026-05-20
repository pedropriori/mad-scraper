import sys
import io
import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright
from rich.console import Console
from rich.panel import Panel

from mad_scraper import auth, discovery, extractor, downloader, writer, progress
from mad_scraper.config import LOGIN_EMAIL, LOGIN_PASSWORD, OUTPUT_DIR, COOKIES_PATH, COURSE_URL, HEADLESS
from mad_scraper.dashboard import Dashboard, DashboardState, HistoryEntry
from mad_scraper.progress import Status

load_dotenv()
if getattr(sys.stdout, 'encoding', '').lower() not in ('utf-8', 'utf_8'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

console = Console(highlight=False)


def _make_progress_callback(state: DashboardState, dash: Dashboard):
    def on_progress(info: dict):
        if info.get("status") != "downloading":
            return
        total = info.get("total_bytes") or info.get("total_bytes_estimate") or 0
        downloaded = info.get("downloaded_bytes") or 0
        speed = info.get("speed") or 0
        eta = info.get("eta") or 0
        state.dl_pct = (downloaded / total * 100) if total else 0
        state.dl_speed_mbps = speed / 1_000_000 if speed else 0
        state.dl_eta_sec = int(eta)
        dash.refresh()
    return on_progress


def run(retry_failed: bool = False, speed_profile: str | None = None) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    progress_path = OUTPUT_DIR / "progress.json"

    if not LOGIN_EMAIL or not LOGIN_PASSWORD:
        console.print("[red]✗ ERRO:[/red] LOGIN_EMAIL e LOGIN_PASSWORD não definidos no .env")
        sys.exit(1)

    console.print(Panel.fit("[bold]MAD Scraper[/bold] — Mentoria American Dream", style="bold blue"))
    console.print()

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

            with console.status("[cyan]Descobrindo aulas...[/cyan]"):
                try:
                    lessons = discovery.get_lessons_with_page(COURSE_URL, page)
                except Exception as e:
                    console.print(f"[red]✗ Discovery FALHOU:[/red] {e}")
                    sys.exit(1)

            if retry_failed:
                failed_urls = set(progress.get_failed(progress_path))
                lessons = [l for l in lessons if l.url in failed_urls]
                console.print(f"[yellow]↻[/yellow] {len(lessons)} aulas para retentar")
            else:
                console.print(f"[green]✓[/green] {len(lessons)} aulas descobertas")
            if speed_profile:
                console.print(f"[cyan]⚡[/cyan] Velocidade: {speed_profile} ({downloader.get_fragment_count(speed_profile)} fragmentos)")

            console.print()
            total = len(lessons)
            ok = 0
            failed_count = 0

            state = DashboardState(total=total)
            with Dashboard(state, console=console) as dash:
                for i, lesson in enumerate(lessons, 1):
                    state.current = i
                    state.current_titulo = lesson.titulo[:55]
                    state.current_modulo = lesson.modulo
                    start = time.time()

                    if not retry_failed and progress.is_done(progress_path, lesson.url):
                        state.add_history(HistoryEntry(index=i, titulo=lesson.titulo[:50], status="skip"))
                        dash.refresh()
                        ok += 1
                        continue

                    state.phase = "scraping"
                    dash.refresh()

                    try:
                        content = extractor.extract_with_page(lesson, page)
                        lesson_dir = writer.write_lesson(content, OUTPUT_DIR)

                        if not content.panda_embed_url:
                            progress.mark(progress_path, lesson.url, Status.DONE)
                            state.add_history(HistoryEntry(index=i, titulo=lesson.titulo[:50], status="skip"))
                            dash.refresh()
                            ok += 1
                            continue

                        state.phase = "download"
                        state.dl_pct = 0.0
                        dash.refresh()
                        on_prog = _make_progress_callback(state, dash)
                        success = downloader.download_video(
                            content.panda_embed_url,
                            lesson_dir,
                            cookies,
                            on_progress=on_prog,
                            speed_profile=speed_profile,
                        )

                        if content.anexos:
                            state.phase = "anexos"
                            dash.refresh()
                            anexos_dir = lesson_dir / "anexos"
                            for att in content.anexos:
                                downloader.download_attachment(att.url, anexos_dir, cookies)

                        dur = int(time.time() - start)
                        if success:
                            progress.mark(progress_path, lesson.url, Status.DONE)
                            state.add_history(HistoryEntry(
                                index=i, titulo=lesson.titulo[:50], status="done", duration_sec=dur
                            ))
                            ok += 1
                        else:
                            progress.mark(progress_path, lesson.url, Status.FAILED)
                            state.add_history(HistoryEntry(index=i, titulo=lesson.titulo[:50], status="failed"))
                            failed_count += 1

                    except Exception as e:
                        progress.mark(progress_path, lesson.url, Status.FAILED)
                        state.add_history(HistoryEntry(index=i, titulo=lesson.titulo[:50], status="failed"))
                        failed_count += 1

                    dash.refresh()

        finally:
            browser.close()

    console.print()
    console.rule()
    if failed_count:
        console.print(f"[bold]Concluído:[/bold] {ok}/{total} OK  [red]{failed_count} falhas[/red]")
        console.print("[yellow]Rode: python cli.py → Retentar aulas com falha[/yellow]")
    else:
        console.print(f"[bold green]Concluído:[/bold green] {ok}/{total} OK — tudo certo!")


if __name__ == "__main__":
    speed = None
    args = sys.argv[1:]
    if "--speed" in args:
        idx = args.index("--speed")
        if idx + 1 < len(args):
            speed = args[idx + 1]
    run(
        retry_failed="--retry-failed" in sys.argv,
        speed_profile=speed,
    )
