import io
import pytest
import string

from contextlib import redirect_stdout
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

    assert hint_cli.parse(["upgrade", "hintr"]) == \
        ("config", None, "upgrade", {"what": "hintr"})
    assert hint_cli.parse(["upgrade", "all"]) == \
        ("config", None, "upgrade", {"what": "all"})


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


def test_verify_data_loss_silent_if_no_loss():
    cfg = hint_deploy.HintConfig("config")
    f = io.StringIO()
    with redirect_stdout(f):
        with mock.patch('src.hint_cli.prompt_yes_no') as prompt:
            prompt.return_value = True
            hint_cli.verify_data_loss("start", {}, cfg)
            hint_cli.verify_data_loss("stop", {"remove_volumes": False}, cfg)

    assert not prompt.called
    assert f.getvalue() == ""


def test_verify_data_loss_warns_if_loss():
    cfg = hint_deploy.HintConfig("config")
    f = io.StringIO()
    with redirect_stdout(f):
        with mock.patch('src.hint_cli.prompt_yes_no') as prompt:
            prompt.return_value = True
            hint_cli.verify_data_loss("stop", {"remove_volumes": True}, cfg)

    assert prompt.called
    assert "WARNING! PROBABLE IRREVERSIBLE DATA LOSS!" in f.getvalue()


def test_verify_data_loss_throws_if_loss():
    cfg = hint_deploy.HintConfig("config")
    with mock.patch('src.hint_cli.prompt_yes_no') as prompt:
        prompt.return_value = False
        with pytest.raises(Exception, match="Not continuing"):
            hint_cli.verify_data_loss("stop", {"remove_volumes": True}, cfg)


def test_verify_data_prevents_unwanted_loss():
    cfg = hint_deploy.HintConfig("config")
    cfg.protect_data = True
    msg = "Cannot remove volumes with this configuration"
    with mock.patch('src.hint_cli.prompt_yes_no') as prompt:
        with pytest.raises(Exception, match=msg):
            hint_cli.verify_data_loss("stop", {"remove_volumes": True}, cfg)


def test_prompt_is_quite_strict():
    assert hint_cli.prompt_yes_no(lambda x: "yes")
    assert not hint_cli.prompt_yes_no(lambda x: "no")
    assert not hint_cli.prompt_yes_no(lambda x: "Yes")
    assert not hint_cli.prompt_yes_no(lambda x: "Great idea!")
    assert not hint_cli.prompt_yes_no(lambda x: "")
