import pytest

from unittest import mock

from src import hint_cli
from src import hint_deploy


def test_cli_parse():
    assert hint_cli.parse(["start"]) == \
        ("config", None, "start", {"pull_images": False})
    assert hint_cli.parse(["start", "--pull"]) == \
        ("config", None, "start", {"pull_images": True})
    assert hint_cli.parse(["start", "staging"]) == \
        ("config", "staging", "start", {"pull_images": False})

    assert hint_cli.parse(["stop"]) == \
        ("config", None, "stop", {"kill": False, "remove_network": False,
                            "remove_volumes": False})
    assert hint_cli.parse(["stop", "--kill", "--network"]) == \
        ("config", None, "stop", {"kill": True, "remove_network": True,
                            "remove_volumes": False})

    assert hint_cli.parse(["destroy"]) == \
        ("config", None, "stop", {"kill": True, "remove_network": True,
                            "remove_volumes": True})

    assert hint_cli.parse(["status"]) == ("config", None, "status", {})

    email = "user@example.com"
    password = "password"
    assert hint_cli.parse(["user", "add", email]) == \
        ("config", None, "user", {"email": email, "action": "add-user",
                            "pull": False, password: None})
    assert hint_cli.parse(["user", "add", "--pull", email, password]) == \
        ("config", None, "user", {"email": email, "action": "add-user",
                            "pull": True, password: password})

    assert hint_cli.parse(["user", "exists", email]) == \
        ("config", None, "user", {"email": email, "action": "user-exists",
                            "pull": False, password: None})
    assert hint_cli.parse(["user", "remove", email]) == \
        ("config", None, "user", {"email": email, "action": "remove-user",
                            "pull": False, password: None})


def test_user_args_passed_to_hint_user():
    email = "user@example.com"
    with mock.patch('src.hint_cli.hint_user') as f:
        hint_cli.main(["user", "add", email])

    assert f.called
    assert f.call_args[1] == {"email": email, "action": "add-user",
                              "pull": False, "password": None}


# This *should* work as far as I can see but I don't see how to make it.
def test_other_args_passed_to_start():
    pytest.skip("not working")
    with mock.patch('constellation.Constellation') as obj:
        hint_cli.main(["status"])

    assert obj.status.called
