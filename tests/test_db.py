import pytest

from remoclip.db import ClipboardEvent, create_session_factory, session_scope


def _make_configured_session_factory(tmp_path):
    db_path = tmp_path / "nested" / "remoclip.sqlite"
    session_factory = create_session_factory(db_path)
    return session_factory, db_path


def test_create_session_factory_creates_database_and_commits(tmp_path):
    session_factory, db_path = _make_configured_session_factory(tmp_path)

    assert db_path.parent.exists(), "Parent directory should be created"

    with session_scope(session_factory) as session:
        session.add(ClipboardEvent(hostname="host", action="copy", content="hello"))

    with session_scope(session_factory) as session:
        events = session.query(ClipboardEvent).all()
        assert len(events) == 1
        assert events[0].hostname == "host"
        assert events[0].action == "copy"
        assert events[0].content == "hello"


def test_session_scope_rolls_back_on_exception(tmp_path):
    session_factory, _ = _make_configured_session_factory(tmp_path)

    with pytest.raises(RuntimeError):
        with session_scope(session_factory) as session:
            session.add(ClipboardEvent(hostname="host", action="copy", content="hello"))
            raise RuntimeError("boom")

    with session_scope(session_factory) as session:
        events = session.query(ClipboardEvent).all()
        assert events == []
