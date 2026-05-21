import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from mad_scraper import downloader

COOKIES = [{
    "name": "session", "value": "abc123", "domain": ".astronmembers.com",
    "path": "/", "secure": True, "expires": 9999999999,
}]
EMBED_URL = "https://player-vz-abc.tv.pandavideo.com.br/embed/?v=xyz"


def _ydl_mock(download_return: int = 0):
    m = MagicMock()
    m.__enter__.return_value = m
    m.download.return_value = download_return
    return m


# ── Existing tests (unchanged) ──────────────────────────────────────────────

def test_returns_true_on_success(tmp_path):
    with patch("mad_scraper.downloader.yt_dlp.YoutubeDL", return_value=_ydl_mock(0)):
        assert downloader.download_video(EMBED_URL, tmp_path, COOKIES) is True


def test_returns_false_on_failure(tmp_path):
    with patch("mad_scraper.downloader.yt_dlp.YoutubeDL", return_value=_ydl_mock(1)):
        assert downloader.download_video(EMBED_URL, tmp_path, COOKIES) is False


def test_passes_video_url_to_ytdlp(tmp_path):
    mock_ydl = _ydl_mock()
    with patch("mad_scraper.downloader.yt_dlp.YoutubeDL", return_value=mock_ydl):
        downloader.download_video(EMBED_URL, tmp_path, COOKIES)
    mock_ydl.download.assert_called_once_with([EMBED_URL])


def test_output_path_in_opts(tmp_path):
    captured: dict = {}

    def fake_ydl(opts):
        captured.update(opts)
        return _ydl_mock()

    with patch("mad_scraper.downloader.yt_dlp.YoutubeDL", side_effect=fake_ydl):
        downloader.download_video(EMBED_URL, tmp_path, COOKIES)

    assert str(tmp_path) in captured.get("outtmpl", "")


def test_cleans_up_temp_cookie_file(tmp_path):
    with patch("mad_scraper.downloader.yt_dlp.YoutubeDL", return_value=_ydl_mock()):
        downloader.download_video(EMBED_URL, tmp_path, COOKIES)
    assert len(list(tmp_path.glob(".tmp_cookies*"))) == 0


# ── New tests ────────────────────────────────────────────────────────────────

def test_get_fragment_count_known_profiles():
    assert downloader.get_fragment_count("eco") == 4
    assert downloader.get_fragment_count("normal") == 16
    assert downloader.get_fragment_count("fast") == 32
    assert downloader.get_fragment_count("ultra") == 64


def test_get_fragment_count_unknown_profile_falls_back_to_config(monkeypatch):
    monkeypatch.setattr(downloader, "CONCURRENT_FRAGMENTS", 16)
    assert downloader.get_fragment_count("invalid") == 16


def test_get_fragment_count_none_falls_back_to_config(monkeypatch):
    monkeypatch.setattr(downloader, "CONCURRENT_FRAGMENTS", 8)
    assert downloader.get_fragment_count(None) == 8


def test_on_progress_hook_included_in_opts(tmp_path):
    captured: dict = {}

    def fake_ydl(opts):
        captured.update(opts)
        return _ydl_mock()

    callback = MagicMock()
    with patch("mad_scraper.downloader.yt_dlp.YoutubeDL", side_effect=fake_ydl):
        downloader.download_video(EMBED_URL, tmp_path, COOKIES, on_progress=callback)

    assert callback in captured.get("progress_hooks", [])


def test_download_attachment_creates_file(tmp_path):
    with patch("mad_scraper.downloader.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.iter_content.return_value = [b"hello world"]
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        result = downloader.download_attachment(
            "https://cdn.example.com/curso-anexo/1/2/3?download=true",
            tmp_path / "anexos",
            COOKIES,
            filename="apostila.pdf",
        )
    assert result is True
    assert (tmp_path / "anexos" / "apostila.pdf").exists()


def test_download_attachment_filename_derived_from_url(tmp_path):
    with patch("mad_scraper.downloader.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.iter_content.return_value = [b"data"]
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        result = downloader.download_attachment(
            "https://cdn.example.com/apostila.pdf",
            tmp_path / "anexos",
            COOKIES,
        )
    assert result is True
    assert (tmp_path / "anexos" / "apostila.pdf").exists()


def test_download_attachment_returns_false_on_error(tmp_path):
    with patch("mad_scraper.downloader.requests.get") as mock_get:
        mock_get.side_effect = Exception("connection error")
        result = downloader.download_attachment(
            "https://cdn.example.com/arquivo.pdf", tmp_path / "anexos", COOKIES
        )
    assert result is False


def _mock_context(ok: bool = True, body: bytes = b"pdf content", raises: bool = False):
    resp = MagicMock()
    resp.ok = ok
    resp.body.return_value = body
    ctx = MagicMock()
    if raises:
        ctx.request.get.side_effect = Exception("network error")
    else:
        ctx.request.get.return_value = resp
    return ctx


def test_download_attachment_with_context_creates_file(tmp_path):
    ctx = _mock_context(ok=True, body=b"pdf content")
    result = downloader.download_attachment_with_context(
        "https://mentoriaamericandr.astronmembers.com/curso-anexo/1/2/3?download=true",
        tmp_path / "anexos",
        ctx,
        filename="apostila.pdf",
    )
    assert result is True
    assert (tmp_path / "anexos" / "apostila.pdf").read_bytes() == b"pdf content"


def test_download_attachment_with_context_returns_false_on_403(tmp_path):
    ctx = _mock_context(ok=False)
    result = downloader.download_attachment_with_context(
        "https://mentoriaamericandr.astronmembers.com/curso-anexo/1/2/3?download=true",
        tmp_path / "anexos",
        ctx,
        filename="arquivo.pdf",
    )
    assert result is False


def test_download_attachment_with_context_returns_false_on_exception(tmp_path):
    ctx = _mock_context(raises=True)
    result = downloader.download_attachment_with_context(
        "https://mentoriaamericandr.astronmembers.com/curso-anexo/1/2/3?download=true",
        tmp_path / "anexos",
        ctx,
        filename="arquivo.pdf",
    )
    assert result is False


def test_download_attachment_with_context_filename_from_url(tmp_path):
    ctx = _mock_context(ok=True, body=b"data")
    result = downloader.download_attachment_with_context(
        "https://mentoriaamericandr.astronmembers.com/curso-anexo/1/2/apostila.pdf",
        tmp_path / "anexos",
        ctx,
    )
    assert result is True
    assert (tmp_path / "anexos" / "apostila.pdf").exists()
