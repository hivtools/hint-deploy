"""
Usage:
  ./hint start [--pull] [<config>]
  ./hint stop  [--volumes] [--network] [--kill] [--force]
  ./hint destroy
  ./hint status
  ./hint upgrade (hintr|all) [<config>]
  ./hint user [--pull] add <email> [<password>]
  ./hint user [--pull] remove <email>
  ./hint user [--pull] exists <email>

Options:
  --pull           Pull images before starting
  --volumes        Remove volumes (WARNING: irreversible data loss)
  --network        Remove network
  --kill           Kill the containers (faster, but possible db corruption)
"""

import docopt
import os
import os.path
import pickle
import time

from src.hint_deploy import \
    HintConfig, \
    hint_constellation, \
    hint_upgrade, \
    hint_user


def parse(argv=None):
    path = "config"
    config = None
    dat = docopt.docopt(__doc__, argv)
    if dat["start"]:
        action = "start"
        config = dat["<config>"]
        args = {"pull_images": dat["--pull"]}
    elif dat["stop"]:
        action = "stop"
        args = {"kill": dat["--kill"],
                "remove_network": dat["--network"],
                "remove_volumes": dat["--volumes"]}
    elif dat["destroy"]:
        action = "stop"
        args = {"kill": True,
                "remove_network": True,
                "remove_volumes": True}
    elif dat["status"]:
        action = "status"
        args = {}
    elif dat["upgrade"]:
        action = "upgrade"
        config = dat["<config>"]
        args = {"what": "hintr" if dat["hintr"] else "all"}
    elif dat["user"]:
        action = "user"
        if dat["add"]:
            user_action = "add-user"
        elif dat["remove"]:
            user_action = "remove-user"
        elif dat["exists"]:
            user_action = "user-exists"
        args = {"email": dat["<email>"],
                "action": user_action,
                "pull": dat["--pull"],
                "password": dat["<password>"]}
    return path, config, action, args


def path_last_deploy(path):
    return path + "/.last_deploy"


def save_config(path, config, cfg):
    dat = {"config": config,
           "time": time.time(),
           "data": cfg}
    with open(path_last_deploy(path), "wb") as f:
        pickle.dump(dat, f)


def read_config(path):
    with open(path_last_deploy(path), "rb") as f:
        dat = pickle.load(f)
    return dat


def load_config(path, config=None, refresh=True):
    if os.path.exists(path_last_deploy(path)):
        dat = read_config(path)
        if refresh:
            print("[Reloaded configuration '{}' ({} s old)]".format(
                dat["config"] or "<base>", round(time.time() - dat["time"])))
            cfg = HintConfig(path, dat["config"])
        else:
            print("[Loaded configuration '{}' ({} s old)]".format(
                dat["config"] or "<base>", round(time.time() - dat["time"])))
            cfg = dat["data"]
    else:
        cfg = HintConfig(path, config)
    return cfg


def remove_config(path):
    p = path_last_deploy(path)
    if os.path.exists(p):
        print("Removing configuration")
        os.unlink(p)


def main(argv=None):
    path, config, action, args = parse(argv)
    refresh = action in ["start", "user"]
    cfg = load_config(path, config, refresh)
    if action == "user":
        hint_user(cfg, **args)
    else:
        obj = hint_constellation(cfg)
        if action == "upgrade":
            hint_upgrade(obj, args["what"])
        else:
            obj.__getattribute__(action)(**args)
        if action == "start" and cfg.add_test_user:
            email = "test.user@example.com"
            pull = args["pull_images"]
            print("Adding test user '{}'".format(email))
            hint_user(cfg, "add-user", email, pull, "password")
        if action == "start":
            save_config(path, config, cfg)
        if action == "stop" and args["remove_volumes"]:
            remove_config(path)
