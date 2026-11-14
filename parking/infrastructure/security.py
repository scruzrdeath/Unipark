"""Security adapters: JWT tokens and an in-memory token denylist."""
from __future__ import annotations

import threading
import time
import uuid
from typing import Dict

import jwt

from parking.domain.errors import InvalidToken
from parking.domain.ports import TokenClaims, TokenDenylist, TokenService


class JwtTokenService(TokenService):
    ALGORITHM = "HS256"
    ISSUER = "unipark"

    def __init__(self, secret: str, expires_minutes: int = 30) -> None:
        if len(secret.encode("utf-8")) < 32:
            raise ValueError("JWT secret must have at least 32 bytes")
        self._secret = secret
        self._minutes = expires_minutes

    def issue(self, subject: str) -> str:
        now = int(time.time())
        payload = {
            "sub": subject, "jti": uuid.uuid4().hex, "iss": self.ISSUER,
            "iat": now, "exp": now + self._minutes * 60,
        }
        return jwt.encode(payload, self._secret, algorithm=self.ALGORITHM)

    def decode(self, token: str) -> TokenClaims:
        try:
            data = jwt.decode(
                token, self._secret, algorithms=[self.ALGORITHM], issuer=self.ISSUER,
                options={"require": ["exp", "sub", "jti", "iss"]},
            )
        except jwt.PyJWTError as exc:
            raise InvalidToken("Invalid or expired token") from exc
        return TokenClaims(subject=data["sub"], token_id=data["jti"], expires_at=float(data["exp"]))


class InMemoryTokenDenylist(TokenDenylist):
    """Single-process denylist. With several workers, use a shared store (database or Redis)."""

    def __init__(self) -> None:
        self._revoked: Dict[str, float] = {}
        self._lock = threading.Lock()

    def revoke(self, token_id: str, expires_at: float) -> None:
        now = time.time()
        with self._lock:
            self._revoked = {k: v for k, v in self._revoked.items() if v > now}  # drop expired entries
            self._revoked[token_id] = expires_at

    def is_revoked(self, token_id: str) -> bool:
        with self._lock:
            return token_id in self._revoked
