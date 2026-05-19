import subprocess
from pathlib import Path

from .auth import cookies_to_netscape


def download_video(
    panda_embed_url: str,
    lesson_dir: Path,
    cookies: list[dict],
    retries: int = 2,
) -> bool:
    cookies_file = lesson_dir / ".tmp_cookies.txt"
    cookies_file.write_text(cookies_to_netscape(cookies), encoding="utf-8")
    try:
        cmd = [
            "yt-dlp",
            "--cookies", str(cookies_file),
            "--output", str(lesson_dir / "video.%(ext)s"),
            "--retries", str(retries),
            "--no-playlist",
            "--add-header", "Referer:https://mentoriaamericandr.astronmembers.com",
            panda_embed_url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    finally:
        cookies_file.unlink(missing_ok=True)
