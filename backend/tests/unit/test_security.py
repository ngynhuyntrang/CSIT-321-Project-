from app.core.security import hash_password, hash_token, new_session_token, verify_password


def test_hash_round_trip():
    stored = hash_password("correct horse 1")
    assert stored.startswith("scrypt$")
    assert verify_password("correct horse 1", stored)


def test_wrong_password_rejected():
    assert not verify_password("wrong password 1", hash_password("correct horse 1"))


def test_same_password_gets_different_salt():
    assert hash_password("correct horse 1") != hash_password("correct horse 1")


def test_malformed_hash_rejected():
    assert not verify_password("anything", "not-a-hash")


def test_token_hash_is_stable_and_not_the_token():
    token = new_session_token()
    assert hash_token(token) == hash_token(token)
    assert hash_token(token) != token
