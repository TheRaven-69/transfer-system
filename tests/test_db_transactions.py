from sqlalchemy import select

from app.db.models import User
from app.db.tx import on_commit, transaction_scope


def test_transaction_rollback_actual_data(db):
    """Verify that database changes are rolled back on exception."""
    try:
        with transaction_scope(db):
            user = User()
            db.add(user)
            db.flush()
            raise RuntimeError("Force Rollback")
    except RuntimeError:
        pass

    result = db.execute(select(User)).scalars().all()
    assert len(result) == 0


def test_nested_transaction_rollback_preserves_outer(db):
    """Verify that a failed nested transaction doesn't roll back the outer one if caught."""
    with transaction_scope(db):
        outer_user = User()
        db.add(outer_user)
        db.flush()

        try:
            with transaction_scope(db):
                inner_user = User()
                db.add(inner_user)
                db.flush()
                raise RuntimeError("Nested Rollback")
        except RuntimeError:
            pass

    result = db.execute(select(User)).scalars().all()
    assert len(result) == 1
    assert result[0].id == outer_user.id


def test_full_session_rollback_clears_all_hooks(db):
    """Verify that if the top-level transaction rolls back, hooks from all levels are cleared."""
    calls = []

    try:
        with transaction_scope(db):
            on_commit(db, calls.append, "outer")
            with transaction_scope(db):
                on_commit(db, calls.append, "inner")
            raise RuntimeError("Full Rollback")
    except RuntimeError:
        pass

    assert calls == []

    with transaction_scope(db):
        on_commit(db, calls.append, "fresh")

    assert calls == ["fresh"]


def test_multi_nesting_transaction_scope(db):
    """Verify multiple levels of nesting work as intended."""
    calls = []
    with transaction_scope(db):
        on_commit(db, calls.append, 1)
        with transaction_scope(db):
            on_commit(db, calls.append, 2)
            with transaction_scope(db):
                on_commit(db, calls.append, 3)

    assert calls == [1, 2, 3]
