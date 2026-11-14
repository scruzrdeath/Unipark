import pytest

pytest.importorskip("bcrypt")

from parking.infrastructure.bcrypt_hasher import BcryptPasswordHasher  # noqa: E402


def test_hash_and_verify():
    h = BcryptPasswordHasher(rounds=4)  # low cost only to keep the test fast
    hashed = h.hash("secret123")
    assert hashed.startswith("$2") and "secret123" not in hashed
    assert h.verify("secret123", hashed)
    assert not h.verify("wrong", hashed)


def test_same_password_gives_different_hashes():
    h = BcryptPasswordHasher(rounds=4)
    assert h.hash("secret123") != h.hash("secret123")


def test_malformed_hash_is_just_false():
    assert BcryptPasswordHasher(rounds=4).verify("x", "not-a-bcrypt-hash") is False
