# -*- coding: utf-8 -*-
import json
import pytest
from pathlib import Path
from mad_scraper.models import Lesson, Comment, LessonContent
from mad_scraper import writer


def _content(
    titulo="Aula de Copywriting",
    modulo="Fundamentos",
    modulo_index=1,
    aula_index=3,
    descricao="Descrição da aula.",
    comentarios=None,
    panda_embed_url="https://player.pandavideo.com.br/embed/?v=abc123",
    duracao_segundos=3600,
):
    if comentarios is None:
        comentarios = [Comment(autor="João Silva", data="2026-01-15", texto="Excelente!")]
    lesson = Lesson(
        url="https://mentoriaamericandr.astronmembers.com/curso/mentoria-american-dream/1/3",
        titulo=titulo,
        modulo=modulo,
        modulo_index=modulo_index,
        aula_index=aula_index,
    )
    return LessonContent(
        lesson=lesson,
        descricao=descricao,
        comentarios=comentarios,
        panda_embed_url=panda_embed_url,
        duracao_segundos=duracao_segundos,
    )


def test_creates_lesson_directory(tmp_path):
    lesson_dir = writer.write_lesson(_content(), tmp_path)
    assert lesson_dir.exists()


def test_lesson_dir_naming_convention(tmp_path):
    lesson_dir = writer.write_lesson(_content(), tmp_path)
    assert lesson_dir.name.startswith("aula-03-")
    assert lesson_dir.parent.name.startswith("modulo-01-")


def test_metadata_json_fields(tmp_path):
    lesson_dir = writer.write_lesson(_content(), tmp_path)
    data = json.loads((lesson_dir / "metadata.json").read_text(encoding="utf-8"))
    assert data["titulo"] == "Aula de Copywriting"
    assert data["modulo"] == "Fundamentos"
    assert data["modulo_index"] == 1
    assert data["aula_index"] == 3
    assert data["curso"] == "Mentoria American Dream"
    assert data["duracao_segundos"] == 3600


def test_comentarios_json_structure(tmp_path):
    lesson_dir = writer.write_lesson(_content(), tmp_path)
    data = json.loads((lesson_dir / "comentarios.json").read_text(encoding="utf-8"))
    assert isinstance(data, list)
    assert data[0]["autor"] == "João Silva"
    assert data[0]["texto"] == "Excelente!"


def test_nota_md_has_frontmatter(tmp_path):
    lesson_dir = writer.write_lesson(_content(), tmp_path)
    text = (lesson_dir / "nota.md").read_text(encoding="utf-8")
    assert text.startswith("---")
    assert "titulo:" in text
    assert "tags:" in text


def test_nota_md_has_descricao(tmp_path):
    lesson_dir = writer.write_lesson(_content(), tmp_path)
    text = (lesson_dir / "nota.md").read_text(encoding="utf-8")
    assert "## Descrição" in text
    assert "Descrição da aula." in text


def test_nota_md_has_comentarios(tmp_path):
    lesson_dir = writer.write_lesson(_content(), tmp_path)
    text = (lesson_dir / "nota.md").read_text(encoding="utf-8")
    assert "## Comentários" in text
    assert "João Silva" in text
    assert "Excelente!" in text


def test_nota_md_no_comentarios_section_when_empty(tmp_path):
    lesson_dir = writer.write_lesson(_content(comentarios=[]), tmp_path)
    text = (lesson_dir / "nota.md").read_text(encoding="utf-8")
    assert "## Comentários" not in text


def test_empty_comentarios_writes_empty_list(tmp_path):
    lesson_dir = writer.write_lesson(_content(comentarios=[]), tmp_path)
    data = json.loads((lesson_dir / "comentarios.json").read_text(encoding="utf-8"))
    assert data == []


def test_slugify_handles_accents():
    assert writer._slugify("Módulo Número Um") == "modulo-numero-um"


def test_slugify_handles_special_chars():
    assert writer._slugify("Aula: Estratégia & Copywriting!") == "aula-estrategia-copywriting"
