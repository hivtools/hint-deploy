"""
Usage:
  ./hint start [--pull] [<configname>]
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
import timeago

from src.hint_deploy import HintConfig, hint_constellation, hint_user


def parse(argv=None):
    path = "config"
    config_name = None
    dat = docopt.docopt(__doc__, argv)
    if dat["start"]:
        action = "start"
        config_name = dat["<configname>"]
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
    return path, config_name, action, args


def path_last_deploy(path):
    return path + "/.last_deploy"


def save_config(path, config_name, cfg):
    dat = {"config_name": config_name,
           "time": time.time(),
           "data": cfg}
    with open(path_last_deploy(path), "wb") as f:
        pickle.dump(dat, f)


def read_config(path):
    with open(path_last_deploy(path), "rb") as f:
        dat = pickle.load(f)
    return dat


def load_config(path, config_name=None, refresh=True):
    if os.path.exists(path_last_deploy(path)):
        dat = read_config(path)
        when = timeago.format(dat["time"])
        if refresh:
            action = "Reloaded"
            cfg = HintConfig(path, dat["config_name"])
        else:
            action = "Loaded"
            cfg = dat["data"]
        print("[{} configuration '{}' ({})]".format(
            action, dat["config_name"] or "<base>", when))
    else:
        cfg = HintConfig(path, config_name)
    return cfg


def remove_config(path):
    p = path_last_deploy(path)
    if os.path.exists(p):
        print("Removing configuration")
        os.unlink(p)


def main(argv=None):
    path, config_name, action, args = parse(argv)
    refresh = action in ["start", "user"]
    cfg = load_config(path, config_name, refresh)
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
            save_config(path, config_name, cfg)
        if action == "stop" and args["remove_volumes"]:
            remove_config(path)
