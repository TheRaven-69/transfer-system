from contextlib import contextmanager
from typing import Any, Callable, cast

from sqlalchemy.orm import Session


def on_commit(db: Session, func: Callable, *args: Any, **kwargs: Any) -> None:
    """
    Registers a function to be called after the current top-level transaction commits.
    Expects to be called within a transaction_scope.
    """
    hooks = getattr(db, "_post_commit_hooks", None)
    if hooks is None:
        hooks = []
        cast(Any, db)._post_commit_hooks = hooks
    hooks.append((func, args, kwargs))


@contextmanager
def transaction_scope(db: Session):
    """
    Starts a new transaction or a SAVEPOINT (nested) if one is already active.
    Ensures that side effects are only executed after a successful top-level commit.
    """
    if db.in_transaction():
        # Nested transaction (SAVEPOINT)
        with db.begin_nested():
            yield
    else:
        # Top-level transaction
        cast(Any, db)._post_commit_hooks = []
        try:
            with db.begin():
                yield

            # If we reached here, the top-level transaction has successfully committed.
            hooks = getattr(db, "_post_commit_hooks", [])
            cast(Any, db)._post_commit_hooks = []
            for f, a, k in hooks:
                try:
                    f(*a, **k)
                except Exception as e:
                    # Isolation: one failing hook doesn't affect others.
                    print(f"Post-commit hook failed: {e}")
        except Exception:
            # Clear hooks on failure to prevent leakage to next transaction
            cast(Any, db)._post_commit_hooks = []
            raise
