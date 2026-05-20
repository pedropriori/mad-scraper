import pytest
from mad_scraper.dashboard import DashboardState, HistoryEntry


def test_dashboard_state_defaults():
    state = DashboardState(total=107)
    assert state.current == 0
    assert state.current_titulo == ""
    assert state.phase == "aguardando"
    assert state.dl_pct == 0.0
    assert state.history == []


def test_add_history_appends_entry():
    state = DashboardState(total=107)
    state.add_history(HistoryEntry(index=1, titulo="Aula 1", status="done"))
    assert len(state.history) == 1
    assert state.history[0].titulo == "Aula 1"


def test_add_history_caps_at_15():
    state = DashboardState(total=107)
    for i in range(20):
        state.add_history(HistoryEntry(index=i, titulo=f"Aula {i}", status="done"))
    assert len(state.history) == 15


def test_add_history_keeps_most_recent():
    state = DashboardState(total=107)
    for i in range(20):
        state.add_history(HistoryEntry(index=i, titulo=f"Aula {i}", status="done"))
    assert state.history[-1].titulo == "Aula 19"
    assert state.history[0].titulo == "Aula 5"


def test_history_entry_defaults():
    entry = HistoryEntry(index=1, titulo="Aula 1", status="done")
    assert entry.duration_sec == 0
