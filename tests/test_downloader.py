import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from mad_scraper import downloader

COOKIES = [{
    "name": "session", "value": "abc123", "domain": ".astronmembers.com",
    "path": "/", "secure": True, "expires": 9999999999,
}]
EMBED_URL = "https://player-vz-abc.tv.pandavideo.com.br/embed/?v=xyz"


def test_returns_true_on_success(tmp_path):
    with patch("mad_scraper.downloader.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assert downloader.download_video(EMBED_URL, tmp_path, COOKIES) is True


def test_returns_false_on_failure(tmp_path):
    with patch("mad_scraper.downloader.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        assert downloader.download_video(EMBED_URL, tmp_path, COOKIES) is False


def test_passes_embed_url_to_ytdlp(tmp_path):
    with patch("mad_scraper.downloader.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        downloader.download_video(EMBED_URL, tmp_path, COOKIES)
        cmd = mock_run.call_args[0][0]
    assert EMBED_URL in cmd


def test_passes_output_path_to_ytdlp(tmp_path):
    with patch("mad_scraper.downloader.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        downloader.download_video(EMBED_URL, tmp_path, COOKIES)
        cmd = mock_run.call_args[0][0]
    assert str(tmp_path) in " ".join(cmd)


def test_cleans_up_temp_cookie_file(tmp_path):
    with patch("mad_scraper.downloader.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        downloader.download_video(EMBED_URL, tmp_path, COOKIES)
    assert len(list(tmp_path.glob(".tmp_cookies*"))) == 0
