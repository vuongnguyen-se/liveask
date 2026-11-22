from liveask import security


def test_codes_have_six_unambiguous_characters():
    for _ in range(500):
        code = security.generate_code()
        assert len(code) == 6
        assert set(code) <= set(security.CODE_ALPHABET)
        assert not set(code) & set("0O1I")


def test_host_tokens_are_long_and_unique():
    tokens = {security.generate_host_token() for _ in range(100)}
    assert len(tokens) == 100
    assert all(len(t) == 43 for t in tokens)


def test_token_hash_roundtrip():
    token = security.generate_host_token()
    stored = security.hash_token(token)
    assert len(stored) == 64
    assert stored != token
    assert security.token_matches(token, stored)
    assert not security.token_matches(token + "x", stored)
