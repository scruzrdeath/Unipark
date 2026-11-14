"""BCrypt password hashing adapter (needs the ``bcrypt`` package)."""
from __future__ import annotations

import bcrypt

from parking.domain.ports import PasswordHasher


class BcryptPasswordHasher(PasswordHasher):
    def __init__(self, rounds: int = 12) -> None:
        self._rounds = rounds

    def hash(self, password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(self._rounds)).decode("ascii")

    def verify(self, password: str, password_hash: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
        except ValueError:  # malformed hash or password too long
            return False
