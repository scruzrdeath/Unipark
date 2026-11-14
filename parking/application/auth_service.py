"""Registration, login (JWT), logout (token revocation). All collaborators come through the constructor."""
from __future__ import annotations

import re
import time
from typing import Callable, Dict, List

from parking.domain.entities import User
from parking.domain.errors import (
    InvalidCredentials,
    InvalidToken,
    TooManyAttempts,
    UsernameTaken,
    WeakPassword,
)
from parking.domain.ports import PasswordHasher, TokenDenylist, TokenService, UserRepository

USERNAME_RE = re.compile(r"^[a-z0-9_.-]{3,40}$")
MIN_PASSWORD_LEN = 8
MAX_PASSWORD_BYTES = 72  # BCrypt only uses the first 72 bytes


def validate_password(password: str) -> None:
    if len(password) < MIN_PASSWORD_LEN:
        raise WeakPassword(f"Password must have at least {MIN_PASSWORD_LEN} characters")
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise WeakPassword(f"Password must have at most {MAX_PASSWORD_BYTES} bytes")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise WeakPassword("Password must contain at least one letter and one digit")


class AuthService:
    def __init__(
        self,
        users: UserRepository,
        hasher: PasswordHasher,
        tokens: TokenService,
        denylist: TokenDenylist,
        max_failed_attempts: int = 5,
        lockout_seconds: float = 60.0,
        time_fn: Callable[[], float] = time.monotonic,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._tokens = tokens
        self._denylist = denylist
        self._max_failed = max_failed_attempts
        self._lockout = lockout_seconds
        self._time = time_fn
        self._failures: Dict[str, List[float]] = {}
        # Used when the user does not exist, so the response time does not reveal valid usernames.
        self._dummy_hash = hasher.hash("dummy-password-1")

    @staticmethod
    def _normalize(username: str) -> str:
        return username.strip().lower()

    def register(self, username: str, password: str) -> User:
        name = self._normalize(username)
        if not USERNAME_RE.match(name):
            raise WeakPassword("Username must have 3 to 40 characters: letters, digits, '.', '_' or '-'")
        validate_password(password)
        if self._users.get_by_username(name) is not None:
            raise UsernameTaken("Username is already taken")
        user = User(username=name, password_hash=self._hasher.hash(password))
        self._users.add(user)  # also raises UsernameTaken if a concurrent request won the race
        return user

    def login(self, username: str, password: str) -> str:
        name = self._normalize(username)
        self._check_not_locked(name)
        user = self._users.get_by_username(name)
        password_ok = self._hasher.verify(password, user.password_hash if user else self._dummy_hash)
        if user is None or not password_ok:
            self._record_failure(name)
            raise InvalidCredentials("Invalid username or password")
        self._failures.pop(name, None)
        return self._tokens.issue(user.username)

    def logout(self, token: str) -> None:
        claims = self._tokens.decode(token)
        self._denylist.revoke(claims.token_id, claims.expires_at)

    def authenticate(self, token: str) -> User:
        claims = self._tokens.decode(token)
        if self._denylist.is_revoked(claims.token_id):
            raise InvalidToken("Token has been revoked")
        user = self._users.get_by_username(claims.subject)
        if user is None:
            raise InvalidToken("Unknown user")
        return user

    # ----- login throttling (brute-force protection) -----
    def _recent_failures(self, name: str) -> List[float]:
        now = self._time()
        recent = [t for t in self._failures.get(name, []) if now - t < self._lockout]
        if recent:
            self._failures[name] = recent
        else:
            self._failures.pop(name, None)
        return recent

    def _check_not_locked(self, name: str) -> None:
        if len(self._recent_failures(name)) >= self._max_failed:
            raise TooManyAttempts("Too many failed attempts. Try again later")

    def _record_failure(self, name: str) -> None:
        self._recent_failures(name)
        self._failures.setdefault(name, []).append(self._time())
        if len(self._failures) > 10_000:  # keep memory bounded
            for key in list(self._failures):
                self._recent_failures(key)
