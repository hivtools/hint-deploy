"""
Usage:
  ./hint start [--pull] [--hintr-branch=<branch>]
               [--hint-branch=<branch>] [<configname>]
  ./hint stop  [--volumes] [--network] [--kill] [--force]
  ./hint destroy
  ./hint status
  ./hint upgrade [--hintr-branch=<branch>] [--hint-branch=<branch>] (hintr|all)
  ./hint user [--pull] add <email> [<password>]
  ./hint user [--pull] remove <email>
  ./hint user [--pull] exists <email>

Options:
  --pull                    Pull images before starting
  --volumes                 Remove volumes (WARNING: irreversible data loss)
  --network                 Remove network
  --kill                    Kill the containers (faster,
                            but possible db corruption)
  --hint-branch=<branch>    The hint branch to deploy
  --hintr-branch=<branch>   The hintr branch to deploy
"""

import docopt
import os
import os.path
import pickle
import time
import timeago

from src.hint_deploy import \
    HintConfig, \
    hint_constellation, \
    hint_start, \
    hint_upgrade_hintr, \
    hint_upgrade_all, \
    hint_user, \
    hint_stop


# Returned options are passed to constellation and override
# configuration in yml e.g. branch to deploy. Args are
# used only in hint-deploy
def parse(argv=None):
    path = "config"
    config_name = None
    dat = docopt.docopt(__doc__, argv)
    if dat["start"]:
        action = "start"
        config_name = dat["<configname>"]
        args = {"pull_images": dat["--pull"]}
        options = {}
        if dat["--hintr-branch"] is not None:
            options["hintr"] = {"tag": dat["--hintr-branch"]}
        if dat["--hint-branch"] is not None:
            options["hint"] = {"tag": dat["--hint-branch"]}
    elif dat["stop"]:
        action = "stop"
        args = {"kill": dat["--kill"],
                "remove_network": dat["--network"],
                "remove_volumes": dat["--volumes"]}
        options = {}
    elif dat["destroy"]:
        action = "stop"
        args = {"kill": True,
                "remove_network": True,
                "remove_volumes": True}
        options = {}
    elif dat["status"]:
        action = "status"
        args = {}
        options = {}
    elif dat["upgrade"]:
        args = {}
        options = {}
        if dat["--hintr-branch"] is not None:
            options["hintr"] = {"tag": dat["--hintr-branch"]}
        if dat["--hint-branch"] is not None:
            options["hint"] = {"tag": dat["--hint-branch"]}
        if dat["hintr"]:
            action = "upgrade_hintr"
        else:
            action = "upgrade_all"
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
        options = {}
    return path, config_name, action, args, options


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


def load_config(path, config_name=None, options=None):
    if os.path.exists(path_last_deploy(path)):
        dat = read_config(path)
        when = timeago.format(dat["time"])
        cfg = HintConfig(path, dat["config_name"], options=options)
        config_name = dat["config_name"]
        print("[Loaded configuration '{}' ({})]".format(
            config_name or "<base>", when))
    else:
        cfg = HintConfig(path, config_name, options=options)
    return config_name, cfg


def remove_config(path):
    p = path_last_deploy(path)
    if os.path.exists(p):
        print("Removing configuration")
        os.unlink(p)


def verify_data_loss(action, args, cfg):
    if action == "stop" and args["remove_volumes"]:
        if cfg.protect_data:
            raise Exception("Cannot remove volumes with this configuration")
        else:
            print("""WARNING! PROBABLE IRREVERSIBLE DATA LOSS!

You are about to delete the data volumes. This action cannot be undone
and will result in the irreversible loss of *all* data associated with
the application. This includes the database, the uploaded files, the
keypairs used to sign login requests, etc.""")

            if not prompt_yes_no():
                raise Exception("Not continuing")


def prompt_yes_no(get_input=input):
    return get_input("\nContinue? [yes/no] ") == "yes"


def main(argv=None):
    path, config_name, action, args, options = parse(argv)
    config_name, cfg = load_config(path, config_name, options)
    obj = hint_constellation(cfg)
    if action == "user":
        hint_user(cfg, **args)
    elif action == "upgrade_hintr":
        hint_upgrade_hintr(obj)
    elif action == "upgrade_all":
        verify_data_loss(action, args, cfg)
        hint_upgrade_all(obj, cfg.db_tag)
    elif action == "start":
        verify_data_loss(action, args, cfg)
        hint_start(obj, cfg, args)
        save_config(path, config_name, cfg)
    elif action == "stop":
        verify_data_loss(action, args, cfg)
        hint_stop(obj)
    else:
        verify_data_loss(action, args, cfg)
        obj.__getattribute__(action)(**args)

        if action == "stop" and args["remove_volumes"]:
            remove_config(path)
