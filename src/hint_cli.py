"""
Usage:
  hint start [--pull]
  hint stop  [--volumes] [--network] [--kill] [--force]
  hint destroy
  hint status
  hint user [--pull] add <email> [<password>]
  hint user [--pull] remove <email>
  hint user [--pull] exists <email>

Options:
  --pull           Pull images before starting
  --volumes        Remove volumes (WARNING: irreversible data loss)
  --network        Remove network
  --kill           Kill the containers (faster, but possible db corruption)
"""

import docopt

from src.hint_deploy import HintConfig, hint_constellation, hint_user


def parse(argv=None):
    path = "config"
    dat = docopt.docopt(__doc__, argv)
    if dat["start"]:
        action = "start"
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
    return path, action, args


def main(argv=None):
    path, action, args = parse(argv)
    cfg = HintConfig(path)
    if action == "user":
        hint_user(cfg, **args)
    else:
        obj = hint_constellation(cfg)
        obj.__getattribute__(action)(**args)
