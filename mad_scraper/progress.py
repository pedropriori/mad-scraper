import json
from enum import Enum
from pathlib import Path


class Status(str, Enum):
    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"


def load(progress_path: Path) -> dict:
    if not progress_path.exists():
        return {}
    return json.loads(progress_path.read_text(encoding="utf-8"))


def save(progress_path: Path, data: dict) -> None:
    progress_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def mark(progress_path: Path, lesson_url: str, status: Status) -> None:
    data = load(progress_path)
    data[lesson_url] = status.value
    save(progress_path, data)


def is_done(progress_path: Path, lesson_url: str) -> bool:
    return load(progress_path).get(lesson_url) == Status.DONE.value


def get_failed(progress_path: Path) -> list[str]:
    return [
        url
        for url, status in load(progress_path).items()
        if status == Status.FAILED.value
    ]
