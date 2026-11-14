"""Test doubles for the security ports (no bcrypt/JWT libraries needed)."""
import itertools

from parking.domain.errors import InvalidToken
from parking.domain.ports import PasswordHasher, TokenClaims, TokenService


class FakeHasher(PasswordHasher):
    def hash(self, password: str) -> str:
        return "hashed:" + password[::-1]

    def verify(self, password: str, password_hash: str) -> bool:
        return password_hash == self.hash(password)


class FakeTokenService(TokenService):
    """Tokens are 'tok-N'. ``expire(token)`` simulates expiration."""

    def __init__(self) -> None:
        self._count = itertools.count(1)
        self._claims = {}

    def issue(self, subject: str) -> str:
        token = f"tok-{next(self._count)}"
        self._claims[token] = TokenClaims(subject, token, 9_999_999_999.0)
        return token

    def decode(self, token: str) -> TokenClaims:
        try:
            return self._claims[token]
        except KeyError:
            raise InvalidToken("Invalid or expired token") from None

    def expire(self, token: str) -> None:
        self._claims.pop(token, None)
