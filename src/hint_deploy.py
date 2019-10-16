import constellation
import constellation.config as config
import constellation.docker_util as docker_util


class HintConfig:
    def __init__(self, path):
        dat = config.read_yaml("{}/hint.yml".format(path))
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
        "hintr", hintr_ref, args=hintr_args, environment=hintr_env)

    # 4. hint
    hint_ref = constellation.ImageReference("mrcide", "hint",
                                            cfg.hint_tag)
    hint_mounts = [constellation.ConstellationMount("uploads", "/uploads")]
    hint_ports = [8080]
    hint = constellation.ConstellationContainer(
        "hint", hint_ref, mounts=hint_mounts, ports=hint_ports,
        configure=hint_configure)

    containers = [db, redis, hintr, hint]

    obj = constellation.Constellation("hint", cfg.prefix, containers,
                                      cfg.network, cfg.volumes, cfg)

    return obj


def db_configure(container, cfg):
    print("[db] Waiting for db to come up")
    docker_util.exec_safely(container, ["wait-for-db"])
    print("[db] Migrating the database")
    nw = docker_util.container_network(container)
    migrate = constellation.ImageReference(
        "mrcide", "hint-db-migrate", cfg.db_tag)
    args = ["-url=jdbc:postgresql://{}/hint".format(container.name)]
    container.client.containers.run(str(migrate), args, network=nw.name,
                                    auto_remove=True, detach=False)


def hint_configure(container, cfg):
    print("[hint] Configuring hint")
    config = {"hintr_url": "http://hintr:8888",
              "upload_dir": "/uploads"}
    config_str = "".join("{}={}\n".format(k, v) for k, v in config.items())
    docker_util.string_into_container(config_str, container,
                                      "/etc/hint/config.properties")
