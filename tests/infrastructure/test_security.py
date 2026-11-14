import time

import pytest

jwt = pytest.importorskip("jwt")

from parking.domain.errors import InvalidToken  # noqa: E402
from parking.infrastructure.security import InMemoryTokenDenylist, JwtTokenService  # noqa: E402

SECRET = "x" * 40


def test_issue_and_decode_roundtrip():
    svc = JwtTokenService(SECRET, expires_minutes=5)
    claims = svc.decode(svc.issue("ana"))
    assert claims.subject == "ana" and claims.token_id
    assert claims.expires_at > time.time()


def test_wrong_secret_rejected():
    token = JwtTokenService(SECRET).issue("ana")
    with pytest.raises(InvalidToken):
        JwtTokenService("y" * 40).decode(token)


def test_expired_token_rejected():
    svc = JwtTokenService(SECRET, expires_minutes=-1)
    with pytest.raises(InvalidToken):
        svc.decode(svc.issue("ana"))


def test_garbage_and_alg_none_rejected():
    svc = JwtTokenService(SECRET)
    with pytest.raises(InvalidToken):
        svc.decode("not-a-token")
    unsigned = jwt.encode({"sub": "ana", "jti": "1", "iss": "unipark", "exp": int(time.time()) + 60},
                          key=None, algorithm="none")
    with pytest.raises(InvalidToken):
        svc.decode(unsigned)


def test_short_secret_refused():
    with pytest.raises(ValueError):
        JwtTokenService("short")


def test_denylist_revokes_and_forgets_expired_entries():
    dl = InMemoryTokenDenylist()
    dl.revoke("a", time.time() + 60)
    assert dl.is_revoked("a") and not dl.is_revoked("b")
    dl.revoke("old", time.time() - 1)
    dl.revoke("new", time.time() + 60)
    assert not dl.is_revoked("old")
