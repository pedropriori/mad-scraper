import yt_dlp
import requests
from pathlib import Path
from typing import Callable, Optional

from .auth import cookies_to_netscape
from .config import CONCURRENT_FRAGMENTS

_REFERER = "https://mentoriaamericandr.astronmembers.com"

SPEED_PROFILES: dict[str, int] = {
    "eco": 4,       # ~20 Mbps — gentle, slow/shared connections
    "normal": 16,   # ~76 Mbps — balanced everyday use
    "fast": 32,     # ~222 Mbps — validated default
    "ultra": 64,    # experimental — gigabit connections
}


def get_fragment_count(profile: Optional[str] = None) -> int:
    if profile and profile in SPEED_PROFILES:
        return SPEED_PROFILES[profile]
    return CONCURRENT_FRAGMENTS


def download_video(
    video_url: str,
    lesson_dir: Path,
    cookies: list[dict],
    retries: int = 2,
    on_progress: Optional[Callable] = None,
    speed_profile: Optional[str] = None,
) -> bool:
    cookies_file = lesson_dir / ".tmp_cookies.txt"
    cookies_file.write_text(cookies_to_netscape(cookies), encoding="utf-8")
    try:
        hooks = [on_progress] if on_progress else []
        opts = {
            "cookiefile": str(cookies_file),
            "outtmpl": str(lesson_dir / "video.%(ext)s"),
            "retries": retries,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "overwrites": True,
            "concurrent_fragment_downloads": get_fragment_count(speed_profile),
            "http_headers": {"Referer": _REFERER},
            "progress_hooks": hooks,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.download([video_url]) == 0
    except Exception:
        return False
    finally:
        cookies_file.unlink(missing_ok=True)


def download_attachment(
    url: str,
    dest_dir: Path,
    cookies: list[dict],
    retries: int = 2,
) -> bool:
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = url.split("/")[-1].split("?")[0] or "anexo"
    dest_path = dest_dir / filename
    session_cookies = {c["name"]: c["value"] for c in cookies}
    headers = {"Referer": _REFERER}
    for attempt in range(retries + 1):
        try:
            resp = requests.get(
                url, cookies=session_cookies, headers=headers, timeout=30, stream=True
            )
            resp.raise_for_status()
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except Exception:
            if attempt == retries:
                return False
    return False
