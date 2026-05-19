import sys
import io
from pathlib import Path
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from mad_scraper import auth, discovery, extractor, downloader, writer, progress
from mad_scraper.config import LOGIN_EMAIL, LOGIN_PASSWORD, OUTPUT_DIR, COOKIES_PATH, COURSE_URL
from mad_scraper.progress import Status

load_dotenv()


def run(retry_failed: bool = False) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    progress_path = OUTPUT_DIR / "progress.json"

    if not LOGIN_EMAIL or not LOGIN_PASSWORD:
        print("ERRO: LOGIN_EMAIL e LOGIN_PASSWORD não definidos no .env")
        sys.exit(1)

    print("→ Fazendo login...")
    try:
        cookies = auth.login(LOGIN_EMAIL, LOGIN_PASSWORD, COOKIES_PATH)
        print("  Login OK")
    except Exception as e:
        print(f"  FALHOU: {e}")
        sys.exit(1)

    print("→ Descobrindo aulas...")
    try:
        lessons = discovery.get_lessons(COURSE_URL, cookies)
    except Exception as e:
        print(f"  FALHOU: {e}")
        sys.exit(1)

    if retry_failed:
        failed_urls = set(progress.get_failed(progress_path))
        lessons = [l for l in lessons if l.url in failed_urls]
        print(f"  Retentando {len(lessons)} aulas com falha")
    else:
        print(f"  {len(lessons)} aulas encontradas")

    total = len(lessons)
    ok = 0
    failed = 0

    for i, lesson in enumerate(lessons, 1):
        if not retry_failed and progress.is_done(progress_path, lesson.url):
            print(f"[{i}/{total}] Pulando (concluída): {lesson.titulo}")
            ok += 1
            continue

        print(f"[{i}/{total}] {lesson.modulo} · {lesson.titulo}")

        try:
            print("  ↳ scraping...")
            content = extractor.extract(lesson, cookies)
            lesson_dir = writer.write_lesson(content, OUTPUT_DIR)

            if not content.panda_embed_url:
                print("  ↳ sem vídeo encontrado, marcando como done (aula só texto)")
                progress.mark(progress_path, lesson.url, Status.DONE)
                ok += 1
                continue

            print("  ↳ download...")
            success = downloader.download_video(content.panda_embed_url, lesson_dir, cookies)

            if success:
                progress.mark(progress_path, lesson.url, Status.DONE)
                print("  ↳ OK")
                ok += 1
            else:
                progress.mark(progress_path, lesson.url, Status.FAILED)
                print("  ↳ FALHOU (vídeo)")
                failed += 1

        except Exception as e:
            progress.mark(progress_path, lesson.url, Status.FAILED)
            print(f"  ↳ FALHOU: {e}")
            failed += 1

    print(f"\n{'='*40}")
    print(f"Concluído: {ok}/{total} OK | {failed} falhas")
    if failed:
        print("Rode com --retry-failed para retentar as falhas")


if __name__ == "__main__":
    run(retry_failed="--retry-failed" in sys.argv)
