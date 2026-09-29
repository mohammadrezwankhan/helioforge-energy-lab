"""Connection lifetime and transaction integrity regressions."""
import sqlite3
import pytest
from helioforge.store import Store


def test_connections_close_after_use(tmp_path):
    store = Store(str(tmp_path/'audit.sqlite3'))
    with store.connect() as db:
        assert db.execute('SELECT 1').fetchone()[0] == 1
    with pytest.raises(sqlite3.ProgrammingError, match='closed'):
        db.execute('SELECT 1')


def test_failed_transaction_rolls_back_and_closes(tmp_path):
    store = Store(str(tmp_path/'audit.sqlite3'))
    with pytest.raises(RuntimeError):
        with store.connect() as db:
            db.execute('INSERT INTO runs VALUES (?,?,?,?,?,?)', ('rollback','test','now','hash','{}','{}'))
            raise RuntimeError('Abort transaction')
    assert store.get_run('rollback') is None
    with pytest.raises(sqlite3.ProgrammingError, match='closed'):
        db.execute('SELECT 1')
