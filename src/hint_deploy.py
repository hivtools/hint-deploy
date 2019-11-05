import docker
import getpass
import math
import re
import requests
import time

import constellation
import constellation.config as config
import constellation.docker_util as docker_util


class HintConfig:
    def __init__(self, path, extra=None):
        dat = config.read_yaml("{}/hint.yml".format(path))
        dat = config.config_build(path, dat, extra)
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

        self.proxy_host = config.config_string(dat, ["proxy", "host"])
        self.proxy_port_http = config.config_integer(dat,
                                                     ["proxy", "port_http"],
                                                     True, 80)
        self.proxy_port_https = config.config_integer(dat,
                                                      ["proxy", "port_https"],
                                                      True, 443)
        self.volumes = {
            "db": config.config_string(dat, ["db", "volume"]),
            "uploads": config.config_string(dat, ["hint", "volume"])}


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

    # 3. hintr (+ workers, for now)
    hintr_ref = constellation.ImageReference("mrcide", "hintr",
                                             cfg.hintr_tag)
    hintr_args = ["--workers=2"]
    hintr_mounts = [constellation.ConstellationMount("uploads", "/uploads")]
    hintr_env = {"REDIS_URL": "redis://{}:6379".format(redis.name)}
    hintr = constellation.ConstellationContainer(
        "hintr", hintr_ref, args=hintr_args, mounts=hintr_mounts,
        environment=hintr_env)

    # 4. hint
    hint_ref = constellation.ImageReference("mrcide", "hint",
                                            cfg.hint_tag)
    hint_mounts = [constellation.ConstellationMount("uploads", "/uploads")]
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

    containers = [db, redis, hintr, hint, proxy]

    obj = constellation.Constellation("hint", cfg.prefix, containers,
                                      cfg.network, cfg.volumes, cfg)

    return obj


def hint_user(cfg, action, email, pull, password=None):
    ref = constellation.ImageReference("mrcide", "hint-user-cli", cfg.hint_tag)
    if pull or not docker_util.image_exists(str(ref)):
        docker_util.image_pull("hint cli", str(ref))
    args = [action, email]
    if action == "add-user":
        args.append(password or getpass.getpass())
    client = docker.client.from_env()
    res = client.containers.run(str(ref), args, network=cfg.network,
                                remove=True, detach=False)
    # clean up output for printing by stripping the Spring banner and
    # preventing too many newlines
    output = res.decode("UTF-8")
    pat = ".*?:: Spring Boot ::[^\n]+\n+"
    print(re.sub(pat, "", output, re.DOTALL, re.S).rstrip())


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
    config = {"hintr_url": "http://hintr:8888",
              "upload_dir": "/uploads"}
    config_str = "".join("{}={}\n".format(k, v) for k, v in config.items())
    docker_util.string_into_container(config_str, container,
                                      "/etc/hint/config.properties")
    print("[hint] Waiting for hint to become responsive")
    wait(lambda: requests.get("http://localhost:8080").status_code == 200,
         "Hint did not become responsive in time")


def proxy_configure(container, cfg):
    print("[proxy] Configuring proxy")
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
