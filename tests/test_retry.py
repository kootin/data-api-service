import pytest
from pymongo.errors import AutoReconnect

from app.repositories.mongo import retry


def test_retry_recovers_from_transient_errors():
    calls = []

    @retry(times=3, backoff=0)
    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise AutoReconnect("blip")
        return "ok"

    assert flaky() == "ok" and len(calls) == 3


def test_retry_gives_up():
    @retry(times=2, backoff=0)
    def down():
        raise AutoReconnect("down")

    with pytest.raises(AutoReconnect):
        down()
