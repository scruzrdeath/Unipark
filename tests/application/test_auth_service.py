import pytest

from parking.application.auth_service import AuthService
from parking.domain.errors import (
    InvalidCredentials,
    InvalidToken,
    TooManyAttempts,
    UsernameTaken,
    WeakPassword,
)
from parking.infrastructure.in_memory import InMemoryUserRepository
from parking.infrastructure.security import InMemoryTokenDenylist
from tests.fakes import FakeHasher, FakeTokenService


class Now:
    t = 0.0

    def __call__(self):
        return self.t


@pytest.fixture
def now():
    return Now()


@pytest.fixture
def tokens():
    return FakeTokenService()


@pytest.fixture
def users():
    return InMemoryUserRepository()


@pytest.fixture
def auth(users, tokens, now):
    return AuthService(users, FakeHasher(), tokens, InMemoryTokenDenylist(),
                       max_failed_attempts=3, lockout_seconds=60, time_fn=now)


def test_register_stores_hash_not_password(auth, users):
    user = auth.register("Ana", "secret123")
    assert user.username == "ana"
    assert "secret123" not in user.password_hash
    assert users.get_by_username("ana") is not None


def test_duplicate_username_rejected_even_with_different_case(auth):
    auth.register("ana", "secret123")
    with pytest.raises(UsernameTaken):
        auth.register("ANA", "other1234")


@pytest.mark.parametrize("password", ["short1", "onlyletters", "12345678", "a1" * 40])
def test_weak_passwords_rejected(auth, password):
    with pytest.raises(WeakPassword):
        auth.register("ana", password)


@pytest.mark.parametrize("name", ["ab", "has space", "a" * 41, "ñandú", "x;drop"])
def test_invalid_usernames_rejected(auth, name):
    with pytest.raises(WeakPassword):
        auth.register(name, "secret123")


def test_login_and_authenticate(auth):
    auth.register("ana", "secret123")
    token = auth.login("ana", "secret123")
    assert auth.authenticate(token).username == "ana"


def test_wrong_password_and_unknown_user_give_same_error(auth):
    auth.register("ana", "secret123")
    with pytest.raises(InvalidCredentials) as wrong:
        auth.login("ana", "badpass999")
    with pytest.raises(InvalidCredentials) as unknown:
        auth.login("nobody", "secret123")
    assert str(wrong.value) == str(unknown.value)


def test_logout_revokes_token(auth):
    auth.register("ana", "secret123")
    token = auth.login("ana", "secret123")
    auth.logout(token)
    with pytest.raises(InvalidToken):
        auth.authenticate(token)


def test_invalid_token_rejected(auth):
    with pytest.raises(InvalidToken):
        auth.authenticate("garbage")


def test_expired_token_rejected(auth, tokens):
    auth.register("ana", "secret123")
    token = auth.login("ana", "secret123")
    tokens.expire(token)
    with pytest.raises(InvalidToken):
        auth.authenticate(token)


def test_account_locks_after_repeated_failures_then_recovers(auth, now):
    auth.register("ana", "secret123")
    for _ in range(3):
        with pytest.raises(InvalidCredentials):
            auth.login("ana", "badpass999")
    with pytest.raises(TooManyAttempts):
        auth.login("ana", "secret123")  # even the right password is blocked
    now.t = 61
    assert auth.login("ana", "secret123")


def test_success_resets_failure_counter(auth):
    auth.register("ana", "secret123")
    for _ in range(2):
        with pytest.raises(InvalidCredentials):
            auth.login("ana", "badpass999")
    auth.login("ana", "secret123")
    for _ in range(2):
        with pytest.raises(InvalidCredentials):
            auth.login("ana", "badpass999")
