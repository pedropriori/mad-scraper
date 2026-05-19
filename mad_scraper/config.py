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
