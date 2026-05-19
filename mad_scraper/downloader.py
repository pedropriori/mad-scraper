import yt_dlp
from pathlib import Path

from .auth import cookies_to_netscape

_REFERER = "https://mentoriaamericandr.astronmembers.com"


def download_video(
    video_url: str,
    lesson_dir: Path,
    cookies: list[dict],
    retries: int = 2,
) -> bool:
    cookies_file = lesson_dir / ".tmp_cookies.txt"
    cookies_file.write_text(cookies_to_netscape(cookies), encoding="utf-8")
    try:
        opts = {
            "cookiefile": str(cookies_file),
            "outtmpl": str(lesson_dir / "video.%(ext)s"),
            "retries": retries,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "overwrites": True,
            "concurrent_fragment_downloads": 32,
            "http_headers": {"Referer": _REFERER},
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.download([video_url]) == 0
    except Exception:
        return False
    finally:
        cookies_file.unlink(missing_ok=True)
