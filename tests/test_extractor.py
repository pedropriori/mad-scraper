import pytest
from mad_scraper import extractor
from mad_scraper.models import Lesson

# Mock HTML matching REAL site structure from Task 5 inspection
MOCK_HTML_WITH_VIDEO_AND_COMMENTS = """
<html><body>
  <div class="videohead"><h6>Call - O que eu faria se começando do zero</h6></div>
  <div class="videodesc">Aprenda os fundamentos do copywriting americano.</div>
  <iframe class="streaming-video-url"
          data-original-url="https://player-vz-abc123.tv.pandavideo.com.br/embed/?v=uuid-456"
          src="https://player-vz-abc123.tv.pandavideo.com.br/embed/?v=uuid-456">
  </iframe>
  <div class="commentbox">
    <!-- Template comment (should be skipped) -->
    <div class="comment comment-box" data-id="{id}">
      <div class="info flex-item">
        <div class="info-head"><a><h4 class="name text-truncate">{nome}</h4></a><p class="time"></p></div>
        <div class="commentdesc-container"><p class="commentdesc">{comment}</p></div>
      </div>
    </div>
    <!-- Real comment 1 -->
    <div class="comment comment-box" data-id="12345">
      <div class="info flex-item">
        <div class="info-head"><a><h4 class="name text-truncate">João Silva</h4></a><p class="time">2026-01-15</p></div>
        <div class="commentdesc-container"><p class="commentdesc">Excelente aula!</p></div>
      </div>
    </div>
    <!-- Real comment 2 -->
    <div class="comment comment-box" data-id="67890">
      <div class="info flex-item">
        <div class="info-head"><a><h4 class="name text-truncate">Maria Costa</h4></a><p class="time">2026-01-16</p></div>
        <div class="commentdesc-container"><p class="commentdesc">Incrível!</p></div>
      </div>
    </div>
  </div>
</body></html>
"""

MOCK_HTML_NO_COMMENTS = """
<html><body>
  <div class="videohead"><h6>Aula Simples</h6></div>
  <div class="videodesc">Só descrição aqui.</div>
  <iframe class="streaming-video-url"
          data-original-url="https://player-vz-abc.tv.pandavideo.com.br/embed/?v=xyz">
  </iframe>
  <div class="nocomments">Seja o primeiro a comentar</div>
</body></html>
"""

MOCK_HTML_NO_VIDEO = """
<html><body>
  <div class="videohead"><h6>Aula Só Texto</h6></div>
  <div class="videodesc">Descrição desta aula de texto.</div>
  <div class="nocomments">Seja o primeiro a comentar</div>
</body></html>
"""


def _lesson():
    return Lesson(
        url="https://mentoriaamericandr.astronmembers.com/curso/mentoria-american-dream/1/1",
        titulo="Aula 1", modulo="Módulo 1", modulo_index=1, aula_index=1,
    )


def test_parse_returns_panda_embed_url():
    content = extractor._parse_html(MOCK_HTML_WITH_VIDEO_AND_COMMENTS, _lesson())
    assert "pandavideo" in content.panda_embed_url


def test_parse_returns_descricao():
    content = extractor._parse_html(MOCK_HTML_WITH_VIDEO_AND_COMMENTS, _lesson())
    assert "copywriting americano" in content.descricao


def test_parse_returns_real_comments_only():
    content = extractor._parse_html(MOCK_HTML_WITH_VIDEO_AND_COMMENTS, _lesson())
    assert len(content.comentarios) == 2


def test_parse_comment_fields():
    content = extractor._parse_html(MOCK_HTML_WITH_VIDEO_AND_COMMENTS, _lesson())
    c = content.comentarios[0]
    assert c.autor == "João Silva"
    assert c.data == "2026-01-15"
    assert c.texto == "Excelente aula!"


def test_parse_returns_empty_comments_when_none():
    content = extractor._parse_html(MOCK_HTML_NO_COMMENTS, _lesson())
    assert content.comentarios == []


def test_parse_returns_empty_panda_url_when_no_video():
    content = extractor._parse_html(MOCK_HTML_NO_VIDEO, _lesson())
    assert content.panda_embed_url == ""


def test_parse_preserves_lesson_reference():
    lesson = _lesson()
    content = extractor._parse_html(MOCK_HTML_WITH_VIDEO_AND_COMMENTS, lesson)
    assert content.lesson is lesson
