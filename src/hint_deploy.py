import docker
import math
import re
import requests
import time

import constellation
import constellation.config as config
import constellation.docker_util as docker_util


class HintConfig:
    def __init__(self, path, config_name=None):
        dat = config.read_yaml("{}/hint.yml".format(path))
        dat = config.config_build(path, dat, config_name)
        self.network = config.config_string(dat, ["docker", "network"])
        self.prefix = config.config_string(dat, ["docker", "prefix"])
        default_tag = config.config_string(dat, ["docker", "default_tag"],
                                           True, "master")
        self.redis_tag = config.config_string(dat, ["redis", "tag"],
                                              True, default_tag)
        self.db_tag = config.config_string(dat, ["db", "tag"],
                                           True, default_tag)
        self.hint_tag = config.config_string(dat, ["hint", "tag"],
                                             True, default_tag)
        self.hint_expose = config.config_boolean(dat, ["hint", "expose"],
                                                 True, False)
        self.hintr_tag = config.config_string(dat, ["hintr", "tag"],
                                              True, default_tag)
        self.hintr_workers = config.config_integer(dat, ["hintr", "workers"])
        self.hintr_use_mock_model = config.config_boolean(
            dat, ["hintr", "use_mock_model"], True, False)

        self.hintr_ref = constellation.ImageReference(
            "mrcide", "hintr", self.hintr_tag)
        self.hintr_worker_ref = constellation.ImageReference(
            "mrcide", "hintr-worker", self.hintr_tag)

        self.hint_email_password = config.config_string(
            dat, ["hint", "email", "password"], True, "")
        self.hint_email_mode = "real" if self.hint_email_password else "disk"

        self.proxy_host = config.config_string(dat, ["proxy", "host"])
        self.proxy_port_http = config.config_integer(dat,
                                                     ["proxy", "port_http"],
                                                     True, 80)
        self.proxy_port_https = config.config_integer(dat,
                                                      ["proxy", "port_https"],
                                                      True, 443)
        self.proxy_url = proxy_url(self.proxy_host, self.proxy_port_https)

        self.proxy_ssl_certificate = config.config_string(
            dat, ["proxy", "ssl", "certificate"], True)
        self.proxy_ssl_key = config.config_string(
            dat, ["proxy", "ssl", "key"], True)
        self.volumes = {
            "db": config.config_string(
                dat, ["db", "volume"]),
            "uploads": config.config_string(
                dat, ["hint", "volumes", "uploads"]),
            "config": config.config_string(
                dat, ["hint", "volumes", "config"]),
            "results": config.config_string(
                dat, ["hintr", "volumes", "results"]),
            "prerun": config.config_string(
                dat, ["hintr", "volumes", "prerun"])
        }
        self.vault = config.config_vault(dat, ["vault"])
        self.add_test_user = config.config_boolean(
            dat, ["users", "add_test_user"], True, False)

        self.protect_data = config.config_boolean(
            dat, ["deploy", "protect_data"], True, False)


def hint_constellation(cfg):
    # 1. The db
    db_ref = constellation.ImageReference(
        "mrcide", "hint-db", cfg.db_tag)
    db_mounts = [constellation.ConstellationMount("db", "/pgdata")]
    db = constellation.ConstellationContainer(
        "db", db_ref, mounts=db_mounts, configure=db_configure)

    # 2. Redis
    redis_ref = constellation.ImageReference("library", "redis",
                                             cfg.redis_tag)
    redis = constellation.ConstellationContainer("redis", redis_ref)

    # 3. hintr
    hintr_ref = cfg.hintr_ref
    hintr_args = ["--workers=0",
                  "--results-dir=/results",
                  "--prerun-dir=/prerun"]
    hintr_mounts = [constellation.ConstellationMount("uploads", "/uploads"),
                    constellation.ConstellationMount("results", "/results"),
                    constellation.ConstellationMount("prerun", "/prerun")]
    hintr_env = {"REDIS_URL": "redis://{}:6379".format(redis.name)}
    if cfg.hintr_use_mock_model:
        hintr_env["USE_MOCK_MODEL"] = "true"
    hintr = constellation.ConstellationContainer(
        "hintr", hintr_ref, args=hintr_args, mounts=hintr_mounts,
        environment=hintr_env)

    # 4. hint
    hint_ref = constellation.ImageReference("mrcide", "hint",
                                            cfg.hint_tag)
    hint_mounts = [constellation.ConstellationMount("uploads", "/uploads"),
                   constellation.ConstellationMount("config", "/etc/hint")]
    hint_ports = [8080] if cfg.hint_expose else None
    hint = constellation.ConstellationContainer(
        "hint", hint_ref, mounts=hint_mounts, ports=hint_ports,
        configure=hint_configure)

    # 5. proxy
    proxy_ref = constellation.ImageReference("reside", "proxy-nginx", "latest")
    proxy_ports = [cfg.proxy_port_http, cfg.proxy_port_https]
    proxy_args = ["hint:8080",
                  cfg.proxy_host,
                  str(cfg.proxy_port_http),
                  str(cfg.proxy_port_https)]
    proxy = constellation.ConstellationContainer(
        "proxy", proxy_ref, ports=proxy_ports, args=proxy_args,
        configure=proxy_configure)

    # 6. hintr workers
    worker_ref = cfg.hintr_worker_ref
    worker = constellation.ConstellationService(
        "worker", worker_ref, cfg.hintr_workers,
        mounts=hintr_mounts, environment=hintr_env)

    containers = [db, redis, hintr, hint, proxy, worker]

    obj = constellation.Constellation("hint", cfg.prefix, containers,
                                      cfg.network, cfg.volumes,
                                      data=cfg, vault_config=cfg.vault)

    return obj


def hint_upgrade_hintr(obj):
    hintr = obj.containers.find("hintr")
    worker = obj.containers.find("worker")
    container = hintr.get(obj.prefix)

    # Always pull the docker image - and do this *before* we start
    # removing things to minimise downtime.
    docker_util.image_pull(hintr.name, str(obj.data.hintr_ref))
    docker_util.image_pull(hintr.name, str(obj.data.hintr_worker_ref))

    if container:
        if container.status == "running":
            print("Stopping previous hintr and workers")
            container.exec_run(["hintr_stop"])
        docker_util.container_remove_wait(container)

    obj.start(subset=[hintr.name, worker.name])


def hint_user(cfg, action, email, pull, password=None):
    ref = constellation.ImageReference("mrcide", "hint-user-cli", cfg.hint_tag)
    if pull or not docker_util.image_exists(str(ref)):
        docker_util.image_pull("hint cli", str(ref))
    args = [action, email]
    if action == "add-user":
        res_exists = hint_user_run(ref, ["user-exists", email], cfg)
        if res_exists.endswith("\ntrue"):
            print("Not adding user {} as they already exist".format(email))
            return
        if password:
            args.append(password)
    hint_user_run(ref, args, cfg)


def hint_user_run(ref, args, cfg):
    client = docker.client.from_env()
    mounts = [docker.types.Mount("/etc/hint", cfg.volumes["config"],
                                 read_only=True)]
    res = client.containers.run(str(ref), args, network=cfg.network,
                                mounts=mounts, remove=True, detach=False)
    output = res.decode("UTF-8").rstrip()
    print(output)
    return output


def db_configure(container, cfg):
    print("[db] Waiting for db to come up")
    docker_util.exec_safely(container, ["wait-for-db"])
    print("[db] Migrating the database")
    migrate = constellation.ImageReference(
        "mrcide", "hint-db-migrate", cfg.db_tag)
    args = ["-url=jdbc:postgresql://{}/hint".format(container.name)]
    container.client.containers.run(str(migrate), args, network=cfg.network,
                                    auto_remove=True, detach=False)


def hint_configure(container, cfg):
    print("[hint] Configuring hint")
    docker_util.exec_safely(container, ["mkdir", "-p", "/etc/hint/token_key"])
    config = {
        "application_url": cfg.proxy_url,
        # drop (start)
        "email_server": "smtp.cc.ic.ac.uk",
        "email_port": 587,
        "email_username": "naomi",
        "email_sender": "naomi-notifications@imperial.ac.uk",
        # drop (end)
        "email_mode": cfg.hint_email_mode,
        "email_password": cfg.hint_email_password,
        "upload_dir": "/uploads",
        "hintr_url": "http://hintr:8888",
        "db_url": "jdbc:postgresql://db/hint",
        "db_password": "changeme"
    }
    config_str = "".join("{}={}\n".format(k, v) for k, v in config.items())
    docker_util.string_into_container(config_str, container,
                                      "/etc/hint/config.properties")
    print("[hint] Waiting for hint to become responsive")
    wait(lambda: requests.get("http://localhost:8080").status_code == 200,
         "Hint did not become responsive in time")


def proxy_configure(container, cfg):
    print("[proxy] Configuring proxy")
    if cfg.proxy_ssl_certificate and cfg.proxy_ssl_key:
        print("Copying ssl certificate and key into proxy")
        docker_util.string_into_container(cfg.proxy_ssl_certificate, container,
                                          "/run/proxy/certificate.pem")
        docker_util.string_into_container(cfg.proxy_ssl_key, container,
                                          "/run/proxy/key.pem")
    else:
        print("Generating self-signed certificates for proxy")
        args = ["self-signed-certificate", "/run/proxy",
                "GB", "London", "IC", "reside", cfg.proxy_host]
        docker_util.exec_safely(container, args)


# It can take a while for the container to come up
def wait(f, message, timeout=30, poll=0.1):
    for i in range(math.ceil(timeout / poll)):
        try:
            if f():
                return
        except Exception:
            pass
        time.sleep(poll)
    raise Exception(message)


def proxy_url(host, port):
    if port == 443:
        return "https://{}".format(host)
    else:
        return "https://{}:{}".format(host, port)
