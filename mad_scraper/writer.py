# -*- coding: utf-8 -*-
import json
import re
from datetime import datetime
from pathlib import Path

from .models import LessonContent


def write_lesson(content: LessonContent, output_dir: Path) -> Path:
    lesson_dir = _lesson_dir(content, output_dir)
    lesson_dir.mkdir(parents=True, exist_ok=True)
    _write_metadata(content, lesson_dir)
    _write_comentarios(content, lesson_dir)
    _write_nota(content, lesson_dir)
    return lesson_dir


def _lesson_dir(content: LessonContent, output_dir: Path) -> Path:
    modulo_slug = _slugify(f"modulo-{content.lesson.modulo_index:02d}-{content.lesson.modulo}")
    aula_slug = _slugify(f"aula-{content.lesson.aula_index:02d}-{content.lesson.titulo}")
    return output_dir / modulo_slug / aula_slug


def _write_metadata(content: LessonContent, lesson_dir: Path) -> None:
    data = {
        "titulo": content.lesson.titulo,
        "modulo": content.lesson.modulo,
        "modulo_index": content.lesson.modulo_index,
        "aula_index": content.lesson.aula_index,
        "curso": "Mentoria American Dream",
        "url": content.lesson.url,
        "data_download": datetime.now().isoformat(timespec="seconds"),
        "duracao_segundos": content.duracao_segundos,
    }
    (lesson_dir / "metadata.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _write_comentarios(content: LessonContent, lesson_dir: Path) -> None:
    data = [{"autor": c.autor, "data": c.data, "texto": c.texto} for c in content.comentarios]
    (lesson_dir / "comentarios.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def _write_nota(content: LessonContent, lesson_dir: Path) -> None:
    modulo_tag = _slugify(f"modulo-{content.lesson.modulo_index:02d}")
    lines = [
        "---",
        f'titulo: "{content.lesson.titulo}"',
        f'modulo: "{content.lesson.modulo}"',
        'curso: "Mentoria American Dream"',
        f'data_download: "{datetime.now().date()}"',
        f'url: "{content.lesson.url}"',
        f"tags: [mentoria, american-dream, {modulo_tag}]",
        "---",
        "",
        f"# {content.lesson.titulo}",
        "",
        "## Descrição",
        content.descricao,
    ]
    if content.comentarios:
        lines += ["", "## Comentários"]
        for c in content.comentarios:
            lines += ["", f"**{c.autor}** · {c.data}", f"> {c.texto}"]
    if content.anexos:
        lines += ["", "## Anexos"]
        for a in content.anexos:
            filename = a.filename or a.url.split("/")[-1].split("?")[0] or a.nome
            lines.append(f"- [{a.nome}](anexos/{filename})")
    (lesson_dir / "nota.md").write_text("\n".join(lines), encoding="utf-8")


def _slugify(text: str) -> str:
    table = str.maketrans(
        "àáâãäåèéêëìíîïòóôõöùúûüçñ",
        "aaaaaaeeeeiiiiooooouuuucn",
    )
    text = text.lower().translate(table)
    text = re.sub(r"[^a-z0-9\-]", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")
