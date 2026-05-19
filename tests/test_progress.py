import pytest
from pathlib import Path
from mad_scraper import progress
from mad_scraper.progress import Status


def test_load_returns_empty_dict_if_no_file(tmp_path):
    assert progress.load(tmp_path / "progress.json") == {}


def test_save_and_load_roundtrip(tmp_path):
    p = tmp_path / "progress.json"
    data = {"https://example.com/aula-1": "done"}
    progress.save(p, data)
    assert progress.load(p) == data


def test_mark_sets_status(tmp_path):
    p = tmp_path / "progress.json"
    progress.mark(p, "https://example.com/aula-1", Status.DONE)
    assert progress.load(p)["https://example.com/aula-1"] == "done"


def test_is_done_returns_true_for_done(tmp_path):
    p = tmp_path / "progress.json"
    progress.mark(p, "https://example.com/aula-1", Status.DONE)
    assert progress.is_done(p, "https://example.com/aula-1") is True


def test_is_done_returns_false_for_failed(tmp_path):
    p = tmp_path / "progress.json"
    progress.mark(p, "https://example.com/aula-1", Status.FAILED)
    assert progress.is_done(p, "https://example.com/aula-1") is False


def test_is_done_returns_false_for_unknown_url(tmp_path):
    assert progress.is_done(tmp_path / "progress.json", "https://example.com/x") is False


def test_get_failed_returns_only_failed_urls(tmp_path):
    p = tmp_path / "progress.json"
    progress.mark(p, "https://example.com/aula-1", Status.DONE)
    progress.mark(p, "https://example.com/aula-2", Status.FAILED)
    progress.mark(p, "https://example.com/aula-3", Status.FAILED)
    assert set(progress.get_failed(p)) == {
        "https://example.com/aula-2",
        "https://example.com/aula-3",
    }


def test_mark_overwrites_existing_status(tmp_path):
    p = tmp_path / "progress.json"
    progress.mark(p, "https://example.com/aula-1", Status.FAILED)
    progress.mark(p, "https://example.com/aula-1", Status.DONE)
    assert progress.is_done(p, "https://example.com/aula-1") is True
