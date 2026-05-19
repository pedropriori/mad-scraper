import pytest
from mad_scraper import discovery
from mad_scraper.models import Lesson

# Mock HTML matching the REAL site structure from inspection
MOCK_HTML = """
<html><body>
<div class="videos">
  <div class="accordion scroll">
    <div class="modulo-head"><h2>Mentoria American Dream</h2></div>
    <dl>
      <dt><div class="head"><div class="content"><h3>Grupo de Whatsapp e Swipe Files</h3></div></div></dt>
      <dd>
        <div class="item"><a href="curso/mentoria-american-dream/125393/707026">
          <li class="aulabox"><div class="item-titulo"><h6>Grupo de Whatsapp do CF</h6></div></li>
        </a></div>
        <div class="item"><a href="curso/mentoria-american-dream/125393/704768">
          <li class="aulabox"><div class="item-titulo"><h6>Billion Swipe File</h6></div></li>
        </a></div>
      </dd>
    </dl>
    <dl>
      <dt><div class="head"><div class="content"><h3>Mentoria American Dream</h3></div></div></dt>
      <dd>
        <div class="item"><a href="curso/mentoria-american-dream/125393/706719">
          <li class="aulabox"><div class="item-titulo"><h6>Sorteio Macbook</h6></div></li>
        </a></div>
      </dd>
    </dl>
  </div>
</div>
</body></html>
"""

BASE = "https://mentoriaamericandr.astronmembers.com"


def test_parse_returns_correct_count():
    lessons = discovery._parse_lessons_html(MOCK_HTML, BASE)
    assert len(lessons) == 3


def test_parse_sets_full_url():
    lessons = discovery._parse_lessons_html(MOCK_HTML, BASE)
    assert lessons[0].url == f"{BASE}/curso/mentoria-american-dream/125393/707026"


def test_parse_sets_titulo():
    lessons = discovery._parse_lessons_html(MOCK_HTML, BASE)
    assert lessons[0].titulo == "Grupo de Whatsapp do CF"


def test_parse_sets_modulo_index():
    lessons = discovery._parse_lessons_html(MOCK_HTML, BASE)
    assert lessons[0].modulo_index == 1
    assert lessons[2].modulo_index == 2


def test_parse_sets_aula_index_within_modulo():
    lessons = discovery._parse_lessons_html(MOCK_HTML, BASE)
    assert lessons[0].aula_index == 1
    assert lessons[1].aula_index == 2
    assert lessons[2].aula_index == 1  # resets per module


def test_parse_sets_modulo_name():
    lessons = discovery._parse_lessons_html(MOCK_HTML, BASE)
    assert lessons[0].modulo == "Grupo de Whatsapp e Swipe Files"
    assert lessons[2].modulo == "Mentoria American Dream"


def test_parse_skips_empty_hrefs():
    html = """
    <html><body><div class="accordion scroll">
      <dl>
        <dt><div class="head"><div class="content"><h3>Módulo 1</h3></div></div></dt>
        <dd>
          <div class="item"><a href=""><li class="aulabox"><h6>Empty href</h6></li></a></div>
          <div class="item"><a href="curso/mentoria-american-dream/125393/111">
            <li class="aulabox"><h6>Valid lesson</h6></li>
          </a></div>
        </dd>
      </dl>
    </div></body></html>
    """
    lessons = discovery._parse_lessons_html(html, BASE)
    assert len(lessons) == 1
    assert lessons[0].titulo == "Valid lesson"
