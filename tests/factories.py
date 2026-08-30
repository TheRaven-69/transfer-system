from itertools import count

from app.db.models import User

_user_sequence = count(1)


def make_user(**overrides) -> User:
    sequence = next(_user_sequence)
    values = {
        "username": f"test_user_{sequence}",
        "email": f"test_user_{sequence}@example.com",
        "password_hash": "test-only-unusable-password-hash",
    }
    values.update(overrides)
    return User(**values)
