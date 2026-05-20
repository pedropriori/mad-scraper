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
            "https://cdn.example.com/apostila.pdf", tmp_path / "anexos", COOKIES
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
