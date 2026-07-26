"""Preference persistence.

Regression cover for the bug where every launch bound a random port, making
each launch a new browser origin and silently wiping all saved settings.
Two things guard against it: the desktop shell now prefers a fixed port
range, and the server mirrors the frontend's localStorage so a port change
is recoverable.
"""
import asyncio
import socket
from contextlib import closing

import pytest

import desktop_app
from backend import config, db


# --- the port must be stable across launches ---------------------------------

def test_preferred_port_range_is_non_empty_and_fixed():
    assert len(desktop_app.PREFERRED_PORTS) > 1
    assert desktop_app.PREFERRED_PORTS[0] == 8800


def test_find_free_port_returns_the_same_port_on_repeated_calls():
    """The whole point of the fix: two launches in a row must land on the
    same origin, or localStorage is wiped between them."""
    first = desktop_app._find_free_port()
    second = desktop_app._find_free_port()
    assert first == second


def test_find_free_port_prefers_the_fixed_range():
    assert desktop_app._find_free_port() in desktop_app.PREFERRED_PORTS


def test_find_free_port_skips_a_port_that_is_already_bound():
    """A second instance must not fail -- it takes the next port in the
    range rather than an unpredictable OS-assigned one."""
    first = desktop_app._find_free_port()
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as taken:
        taken.bind(("127.0.0.1", first))
        taken.listen(1)
        second = desktop_app._find_free_port()
    assert second != first
    assert second in desktop_app.PREFERRED_PORTS


def test_port_is_free_reports_false_for_a_bound_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen(1)
        port = taken.getsockname()[1]
        assert desktop_app._port_is_free(port) is False


# --- the server-side mirror --------------------------------------------------

@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    """A throwaway SQLite file so the test never touches real user data."""
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    asyncio.run(db.init_db())
    yield
    asyncio.run(db.close_db())


def test_prefs_round_trip(temp_db):
    async def run():
        await db.set_prefs({"pulsechart_theme": "light", "pulsechart_vwap": "1"})
        return await db.get_prefs()

    stored = asyncio.run(run())
    assert stored == {"pulsechart_theme": "light", "pulsechart_vwap": "1"}


def test_setting_the_same_key_twice_updates_rather_than_duplicating(temp_db):
    async def run():
        await db.set_prefs({"pulsechart_theme": "dark"})
        await db.set_prefs({"pulsechart_theme": "light"})
        return await db.get_prefs()

    stored = asyncio.run(run())
    assert stored == {"pulsechart_theme": "light"}


def test_empty_prefs_payload_is_a_no_op(temp_db):
    async def run():
        await db.set_prefs({})
        return await db.get_prefs()

    assert asyncio.run(run()) == {}


def test_prefs_survive_values_containing_json(temp_db):
    """Drawings and recents are stored as serialised JSON strings, so the
    mirror must treat values as opaque text and not re-encode them."""
    payload = '{"AAPL":[{"kind":"fib","a":1.5,"b":2.5}]}'

    async def run():
        await db.set_prefs({"pulsechart_drawings_v1": payload})
        return await db.get_prefs()

    assert asyncio.run(run())["pulsechart_drawings_v1"] == payload
