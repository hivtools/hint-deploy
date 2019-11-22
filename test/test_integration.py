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
    assert "Login" in res.content.decode("UTF-8")

    assert docker_util.network_exists("hint_nw")
    assert docker_util.volume_exists("hint_db_data")
    assert docker_util.volume_exists("hint_uploads")
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
    assert not docker_util.container_exists("hint_db")
    assert not docker_util.container_exists("hint_redis")
    assert not docker_util.container_exists("hint_hintr")
    assert not docker_util.container_exists("hint_hint")
    assert len(docker_util.containers_matching("hint_worker_", False)) == 0


def test_start_hint_from_cli():
    if os.path.exists("config/.last_deploy"):
        os.remove("config/.last_deploy")
    hint_cli.main(["start"])
    res = requests.get("http://localhost:8080")
    assert res.status_code == 200
    assert "Login" in res.content.decode("UTF-8")
    assert os.path.exists("config/.last_deploy")
    hint_cli.main(["stop"])
    assert os.path.exists("config/.last_deploy")
    with mock.patch('src.hint_cli.prompt_yes_no') as prompt:
        prompt.return_value = True
        hint_cli.main(["destroy"])
    assert not os.path.exists("config/.last_deploy")


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
    assert "Stopping previous hintr and workers" in p
    assert "Starting hintr" in p
    assert "Starting *service* worker" in p

    assert docker_util.network_exists("hint_nw")
    assert docker_util.volume_exists("hint_db_data")
    assert docker_util.volume_exists("hint_uploads")
    assert docker_util.container_exists("hint_db")
    assert docker_util.container_exists("hint_redis")
    assert docker_util.container_exists("hint_hintr")
    assert docker_util.container_exists("hint_hint")
    assert len(docker_util.containers_matching("hint_worker_", False)) == 2
    assert len(docker_util.containers_matching("hint_worker_", True)) == 4

    f = io.StringIO()
    with redirect_stdout(f):
        hint_cli.main(["upgrade", "all"])

    p = f.getvalue()
    assert "Pulling docker image db" in p
    assert "Stop 'redis'" in p
    assert "Removing 'redis'" in p
    assert "Starting redis" in p

    assert docker_util.network_exists("hint_nw")
    assert docker_util.volume_exists("hint_db_data")
    assert docker_util.volume_exists("hint_uploads")
    assert docker_util.container_exists("hint_db")
    assert docker_util.container_exists("hint_redis")
    assert docker_util.container_exists("hint_hintr")
    assert docker_util.container_exists("hint_hint")
    assert len(docker_util.containers_matching("hint_worker_", False)) == 2

    cfg = hint_deploy.HintConfig("config")
    obj = hint_deploy.hint_constellation(cfg)
    obj.destroy()
