from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Any

from sqlalchemy.orm import Session

PostCommitHook = tuple[Callable[..., Any], tuple[Any, ...], dict[str, Any]]
POST_COMMIT_HOOKS_KEY = "post_commit_hooks"


def _post_commit_hooks(db: Session) -> list[PostCommitHook]:
    hooks = db.info.setdefault(POST_COMMIT_HOOKS_KEY, [])
    return hooks


def on_commit(db: Session, func: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
    """
    Registers a function to be called after the current top-level transaction commits.
    Expects to be called within a transaction_scope.
    """
    _post_commit_hooks(db).append((func, args, kwargs))


@contextmanager
def transaction_scope(db: Session) -> Generator[None, None, None]:
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
        db.info[POST_COMMIT_HOOKS_KEY] = []
        try:
            with db.begin():
                yield

            # If we reached here, the top-level transaction has successfully committed.
            hooks = _post_commit_hooks(db)
            db.info[POST_COMMIT_HOOKS_KEY] = []
            for f, a, k in hooks:
                try:
                    f(*a, **k)
                except Exception as e:
                    # Isolation: one failing hook doesn't affect others.
                    print(f"Post-commit hook failed: {e}")
        except Exception:
            # Clear hooks on failure to prevent leakage to next transaction
            db.info[POST_COMMIT_HOOKS_KEY] = []
            raise
