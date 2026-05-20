import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://mentoriaamericandr.astronmembers.com"
COURSE_URL = f"{BASE_URL}/curso/mentoria-american-dream"
LOGIN_URL = f"{BASE_URL}/entrar"

COOKIES_PATH = Path(".cookies.json")
LOGIN_EMAIL: str = os.getenv("LOGIN_EMAIL", "")
LOGIN_PASSWORD: str = os.getenv("LOGIN_PASSWORD", "")
OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "mentoria-american-dream"))

# AUTH_HEADLESS=false → browser visible for login (safe for captcha/2FA)
AUTH_HEADLESS: bool = os.getenv("AUTH_HEADLESS", "false").lower() == "true"

# HEADLESS=true → scraping runs in background (default changed from v1)
HEADLESS: bool = os.getenv("HEADLESS", "true").lower() == "true"

# concurrent_fragment_downloads for yt-dlp HLS download
CONCURRENT_FRAGMENTS: int = int(os.getenv("CONCURRENT_FRAGMENTS", "32"))
