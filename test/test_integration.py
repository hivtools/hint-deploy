import docker
import json
import io
import os.path
import pytest
import requests
import time

from contextlib import redirect_stdout
from unittest import mock

import constellation
import constellation.docker_util as docker_util

from src import hint_cli, hint_deploy


def test_start_hint():
    cfg = hint_deploy.HintConfig("config")
    obj = hint_deploy.hint_constellation(cfg)
    obj.status()
    obj.start()

    res = requests.get("http://localhost:8080")

    assert res.status_code == 200
    assert "Naomi" in res.content.decode("UTF-8")

    res = requests.get("http://localhost:8888")

    assert res.status_code == 200

    assert docker_util.network_exists("hint_nw")
    assert docker_util.volume_exists("hint_db_data")
    assert docker_util.volume_exists("hint_uploads")
    assert docker_util.volume_exists("hint_results")
    assert docker_util.volume_exists("hint_prerun")
    assert docker_util.container_exists("hint_db")
    assert docker_util.container_exists("hint_redis")
    assert docker_util.container_exists("hint_hintr")
    assert docker_util.container_exists("hint_hint")
    assert len(docker_util.containers_matching("hint_worker_", False)) == 2

    # Some basic user management
    user = "test@example.com"
    f = io.StringIO()
    with redirect_stdout(f):
        hint_deploy.hint_user(cfg, "add-user", user, True, "password")

    p = f.getvalue()
    assert "Adding user {}".format(user) in p
    assert p.strip().split("\n")[-1] == "OK"

    f = io.StringIO()
    with redirect_stdout(f):
        hint_deploy.hint_user(cfg, "user-exists", user, False)

    assert f.getvalue() == "Checking if user exists: {}\ntrue\n".format(user)

    f = io.StringIO()
    with redirect_stdout(f):
        hint_deploy.hint_user(cfg, "add-user", user, True, "password")

    p = f.getvalue()
    assert "Not adding user {} as they already exist".format(user) in p

    f = io.StringIO()
    with redirect_stdout(f):
        hint_deploy.hint_user(cfg, "remove-user", user, False)

    assert f.getvalue() == "Removing user {}\nOK\n".format(user)

    # Confirm we have brought up exactly two workers (none in the
    # hintr container itself)
    script = 'message(httr::content(httr::GET(' + \
             '"http://localhost:8888/hintr/worker/status"),' + \
             '"text", encoding="UTF-8"))'
    args = ["Rscript", "-e", script]
    hintr = obj.containers.get("hintr", obj.prefix)
    result = docker_util.exec_safely(hintr, args).output
    logs = result.decode("UTF-8")
    data = json.loads(logs)["data"]
    assert len(data.keys()) == 2

    obj.destroy()

    assert not docker_util.network_exists("hint_nw")
    assert not docker_util.volume_exists("hint_db_data")
    assert not docker_util.volume_exists("hint_uploads")
    assert not docker_util.volume_exists("hint_results")
    assert not docker_util.volume_exists("hint_prerun")
    assert not docker_util.container_exists("hint_db")
    assert not docker_util.container_exists("hint_redis")
    assert not docker_util.container_exists("hint_hintr")
    assert not docker_util.container_exists("hint_hint")
    assert len(docker_util.containers_matching("hint_worker_", False)) == 0


def test_start_hint_from_cli():
    if os.path.exists("config/.last_deploy"):
        os.remove("config/.last_deploy")

    # Need a dummy extra configuration file that does not trigger the
    # vault
    with open("config/other.yml", "w") as f:
        f.write("proxy:\n host: localhost")

    hint_cli.main(["start", "other"])
    res = requests.get("http://localhost:8080")
    assert res.status_code == 200
    assert "Naomi" in res.content.decode("UTF-8")
    assert os.path.exists("config/.last_deploy")
    assert hint_cli.read_config("config")["config_name"] == "other"
    hint_cli.main(["stop", "--kill"])
    assert os.path.exists("config/.last_deploy")
    assert hint_cli.read_config("config")["config_name"] == "other"
    hint_cli.main(["start"])
    assert os.path.exists("config/.last_deploy")
    assert hint_cli.read_config("config")["config_name"] == "other"

    with mock.patch('src.hint_cli.prompt_yes_no') as prompt:
        prompt.return_value = True
        hint_cli.main(["destroy"])
    assert not os.path.exists("config/.last_deploy")
    os.remove("config/other.yml")


# this checks that specifying the ssl certificates in the
# configuration copies them into the container, but does not involve
# vault or the full deployment - it's all super minimal.
def test_configure_proxy():
    cfg = hint_deploy.HintConfig("config", "staging")
    cl = docker.client.from_env()
    args = ["localhost:80", "localhost", "80", "443"]
    container = cl.containers.run("reside/proxy-nginx:master", args,
                                  detach=True, auto_remove=False)
    args = ["self-signed-certificate", "/tmp",
            "GB", "London", "IC", "reside", cfg.proxy_host]
    docker_util.exec_safely(container, args)
    cert = docker_util.string_from_container(container, "/tmp/certificate.pem")
    key = docker_util.string_from_container(container, "/tmp/key.pem")
    cfg.proxy_ssl_certificate = cert
    cfg.proxy_ssl_key = key
    hint_deploy.proxy_configure(container, cfg)
    assert docker_util.string_from_container(
        container, "/run/proxy/certificate.pem") == cert
    assert docker_util.string_from_container(
        container, "/run/proxy/key.pem") == key
    container.kill()


def test_update_hintr_and_all():
    hint_cli.main(["start"])

    f = io.StringIO()
    with redirect_stdout(f):
        hint_cli.main(["upgrade", "hintr"])

    p = f.getvalue()
    assert "Pulling docker image hintr" in p
    assert "Pulling docker image db-migrate" not in p
    assert "Stopping previous hintr and workers" in p
    assert "Starting hintr" in p
    assert "Starting *service* worker" in p

    assert docker_util.network_exists("hint_nw")
    assert docker_util.volume_exists("hint_db_data")
    assert docker_util.volume_exists("hint_uploads")
    assert docker_util.volume_exists("hint_results")
    assert docker_util.volume_exists("hint_prerun")
    assert docker_util.container_exists("hint_db")
    assert docker_util.container_exists("hint_redis")
    assert docker_util.container_exists("hint_hintr")
    assert docker_util.container_exists("hint_hint")
    assert len(docker_util.containers_matching("hint_worker_", False)) == 2
    assert len(docker_util.containers_matching("hint_worker_", True)) == 4

    # We are going to write some data into redis here and later check
    # that it survived the upgrade.
    cfg = hint_deploy.HintConfig("config")
    obj = hint_deploy.hint_constellation(cfg)
    args_set = ["redis-cli", "SET", "data_persists", "yes"]
    redis = obj.containers.get("redis", obj.prefix)
    docker_util.exec_safely(redis, args_set)

    f = io.StringIO()
    with redirect_stdout(f):
        hint_cli.main(["upgrade", "all"])

    p = f.getvalue()
    assert "Pulling docker image db" in p
    assert "Pulling docker image db-migrate" in p
    assert "Stop 'redis'" in p
    assert "Removing 'redis'" in p
    assert "Starting redis" in p

    assert docker_util.network_exists("hint_nw")
    assert docker_util.volume_exists("hint_db_data")
    assert docker_util.volume_exists("hint_uploads")
    assert docker_util.volume_exists("hint_results")
    assert docker_util.volume_exists("hint_prerun")
    assert docker_util.container_exists("hint_db")
    assert docker_util.container_exists("hint_redis")
    assert docker_util.container_exists("hint_hintr")
    assert docker_util.container_exists("hint_hint")
    assert len(docker_util.containers_matching("hint_worker_", False)) == 2

    redis = obj.containers.get("redis", obj.prefix)
    args_get = ["redis-cli", "GET", "data_persists"]
    result = docker_util.exec_safely(redis, args_get).output.decode("UTF-8")
    assert "yes" in result

    obj.destroy()


def test_start_pulls_db_migrate():
    cfg = hint_deploy.HintConfig("config")
    obj = hint_deploy.hint_constellation(cfg)

    f = io.StringIO()
    with redirect_stdout(f):
        hint_deploy.hint_start(obj, cfg, {"pull_images": True})
    p = f.getvalue()

    assert "Pulling docker image db-migrate" in p

    obj.destroy()

    # Start without --pull doesn't pull migrate image
    f = io.StringIO()
    with redirect_stdout(f):
        hint_deploy.hint_start(obj, cfg, {"pull_images": False})
    p = f.getvalue()

    assert "Pulling docker image db-migrate" not in p

    obj.destroy()


def test_configure_adr_keys():
    cfg = hint_deploy.HintConfig("config")
    with open("key/public_key.der", "rb") as f:
        cfg.hint_key_public = f.read()

    with open("key/private_key.der", "rb") as f:
        cfg.hint_key_private = f.read()

    obj = hint_deploy.hint_constellation(cfg)
    obj.start()

    hint = obj.containers.find("hint").get(obj.prefix)
    assert docker_util.bytes_from_container(
        hint, "/etc/hint/token_key/public_key.der") == cfg.hint_key_public
    assert docker_util.bytes_from_container(
        hint, "/etc/hint/token_key/private_key.der") == cfg.hint_key_private

    obj.destroy()
