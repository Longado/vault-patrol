"""HMAC verification is the only thing standing between the internet and a patrol run."""
import hashlib
import hmac

import pytest
from fastapi import HTTPException

from app.main import _verify

BODY = b'{"zen":"design for failure"}'


def _sig(secret: bytes) -> str:
    return "sha256=" + hmac.new(secret, BODY, hashlib.sha256).hexdigest()


def test_good_signature_passes(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "s3cret")
    _verify(BODY, _sig(b"s3cret"))  # does not raise


@pytest.mark.parametrize("signature", [None, "", "sha1=abc", _sig(b"wrong-secret")])
def test_bad_or_missing_signature_is_401(monkeypatch, signature):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "s3cret")
    with pytest.raises(HTTPException) as e:
        _verify(BODY, signature)
    assert e.value.status_code == 401


def test_unconfigured_secret_is_500_not_a_silent_pass(monkeypatch):
    monkeypatch.delenv("GITHUB_WEBHOOK_SECRET", raising=False)
    with pytest.raises(HTTPException) as e:
        _verify(BODY, _sig(b"s3cret"))
    assert e.value.status_code == 500
