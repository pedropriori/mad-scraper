from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Lesson:
    url: str
    titulo: str
    modulo: str
    modulo_index: int
    aula_index: int


@dataclass
class Comment:
    autor: str
    data: str
    texto: str


@dataclass
class Attachment:
    nome: str
    url: str


@dataclass
class LessonContent:
    lesson: Lesson
    descricao: str
    comentarios: list[Comment]
    panda_embed_url: str
    duracao_segundos: Optional[int] = None
    anexos: list[Attachment] = field(default_factory=list)
