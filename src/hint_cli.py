"""
Usage:
  hint start [--pull]
  hint stop  [--volumes] [--network] [--kill] [--force]
  hint destroy
  hint status

Options:
  --pull           Pull images before starting
  --volumes        Remove volumes (WARNING: irreversible data loss)
  --network        Remove network
  --kill           Kill the containers (faster, but possible db corruption)
"""

import docopt

from src.hint_deploy import HintConfig, hint_constellation


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
    return path, action, args


def main(argv=None):
    path, action, args = parse(argv)
    obj = hint_constellation(HintConfig(path))
    obj.__getattribute__(action)(**args)
