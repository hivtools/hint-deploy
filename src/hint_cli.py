"""
Usage:
  ./hint start [--pull] [<config>]
  ./hint stop  [--volumes] [--network] [--kill] [--force]
  ./hint destroy
  ./hint status
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

from src.hint_deploy import HintConfig, hint_constellation, hint_user


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


def load_config(path, config=None):
    if os.path.exists(path_last_deploy(path)):
        cfg = read_config(path)["data"]
    else:
        cfg = HintConfig(path, config)
    return cfg


def remove_config(path):
    p = path_last_deploy(path)
    if os.path.exists(p):
        print("removing configuration")
        os.unlink(p)


def main(argv=None):
    path, config, action, args = parse(argv)
    cfg = load_config(path, config)
    if action == "user":
        hint_user(cfg, **args)
    else:
        obj = hint_constellation(cfg)
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
