import pytest

from src.hint_deploy import wait

def test_wait_errors_on_timeout():
    with pytest.raises(Exception, match="my message"):
        wait(lambda: False, "my message", 0.1, 0.1)
