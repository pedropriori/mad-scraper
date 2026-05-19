import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from mad_scraper import auth


def _cookie(name="session", value="abc", domain=".astronmembers.com"):
    return {"name": name, "value": value, "domain": domain,
            "path": "/", "secure": True, "expires": 9999999999}


def test_login_saves_cookies_to_file(tmp_path):
    cookies = [_cookie()]
    cookies_path = tmp_path / "cookies.json"

    mock_context = MagicMock()
    mock_context.cookies.return_value = cookies
    mock_page = MagicMock()
    mock_page.context = mock_context
    mock_browser = MagicMock()
    mock_browser.new_page.return_value = mock_page
    mock_pw = MagicMock()
    mock_pw.chromium.launch.return_value = mock_browser

    with patch("mad_scraper.auth.sync_playwright") as mock_sp:
        mock_sp.return_value.__enter__.return_value = mock_pw
        result = auth.login("user@email.com", "pass", cookies_path)

    assert cookies_path.exists()
    assert json.loads(cookies_path.read_text()) == cookies
    assert result == cookies


def test_load_cookies_reads_file(tmp_path):
    cookies = [_cookie()]
    p = tmp_path / "cookies.json"
    p.write_text(json.dumps(cookies))
    assert auth.load_cookies(p) == cookies


def test_load_cookies_raises_if_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        auth.load_cookies(tmp_path / "missing.json")


def test_cookies_to_netscape_format():
    netscape = auth.cookies_to_netscape([_cookie(name="sid", value="xyz")])
    assert "# Netscape HTTP Cookie File" in netscape
    lines = netscape.split("\n")
    parts = lines[1].split("\t")
    assert len(parts) == 7
    assert parts[0] == ".astronmembers.com"
    assert parts[1] == "TRUE"   # subdomain
    assert parts[2] == "/"      # path
    assert parts[3] == "TRUE"   # secure
    assert parts[4] == "9999999999"
    assert parts[5] == "sid"
    assert parts[6] == "xyz"
