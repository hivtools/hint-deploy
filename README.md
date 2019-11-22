# hint-deploy

[![Build Status](https://travis-ci.org/mrc-ide/hint-deploy.svg?branch=master)](https://travis-ci.org/mrc-ide/hint-deploy)
[![codecov.io](https://codecov.io/github/mrc-ide/hint-deploy/coverage.svg?branch=master)](https://codecov.io/github/mrc-ide/hint-deploy?branch=master)

Deployment scripts for [hint](https://github.com/mrc-ide/hint)

## Installation

Clone the repo anywhere and install dependencies with (from the repo root):

```
pip3 install --user -r requirements.txt
```

## Usage

<!-- Regenerate the usage section below by running ./scripts/build_readme -->

<!-- Usage begin -->
```
Usage:
  ./hint start [--pull] [<configname>]
  ./hint stop  [--volumes] [--network] [--kill] [--force]
  ./hint destroy
  ./hint status
  ./hint upgrade (hintr|all)
  ./hint user [--pull] add <email> [<password>]
  ./hint user [--pull] remove <email>
  ./hint user [--pull] exists <email>

Options:
  --pull           Pull images before starting
  --volumes        Remove volumes (WARNING: irreversible data loss)
  --network        Remove network
  --kill           Kill the containers (faster, but possible db corruption)
```
<!-- Usage end -->

Once a configuration is set during `start`, it will be reused by subsequent commands (`stop`, `status`, `upgrade`, `user`, etc) and removed during `destroy`.  The configuration usage information is stored in `config/.last_deploy`.

## Deployment onto the servers

We have two copies of hint deployed:

- [production](https://naomi.dide.ic.ac.uk) is `https://naomi.dide.ic.ac.uk`
- [staging](https://naomi.dide.ic.ac.uk:10443) is `https://naomi.dide.ic.ac.uk:10443`

To get onto production, ssh to `naomi.dide` as the `hint` user with

```
ssh hint@naomi.dide.ic.ac.uk
```

your public key should be added to the `.ssh/authorized_users` file.

To get onto the staging server, from production run `./ssh-staging`

### Preliminary actions

On both machines, deployment is done from the `hint-deploy` directory, and you should `cd` into this directory.

Be aware you may need to upgrade the deploy tool by running `git pull` in the `hint-deploy` directory first.

### Is hintr running?

Run

```
./hint status
```

which will print information like:

```
[Loaded configuration 'staging' (5 minutes ago)]
Constellation hint
  * Network:
    - hint_nw: created
  * Volumes:
    - db (hint_db_data): created
    - uploads (hint_uploads): created
    - config (hint_config): created
  * Containers:
    - db (hint_db): running
    - redis (hint_redis): running
    - hintr (hint_hintr): running
    - hint (hint_hint): running
    - proxy (hint_proxy): running
    - worker (hint_worker_<i>): running (2)
```

The first line indicates the active configuration (see [`config/`](config)).  The number in brackets on the last line indicates the number of workers.  Hopefully everything else is self explanatory.

### Starting a copy of hint that has stopped

On machine reboot, hint will not restart automatically ([mrc-735](https://vimc.myjetbrains.com/youtrack/issue/mrc-735)), so you may need to start hint up with:

```
./hint start
```

if it has already been run you do not need to provide the instance name (staging or production) though adding it is harmless.  You will be prompted for your github token during startup.

If you want to update images at the same time, run

```
./hint start --pull
```

### Upgrading a running copy of hint

This will pull new containers, take down the system and bring up the new copy.  Downtime likely to be ~1 minute as containers are stopped and brought back up.  You will be prompted for your github token during this process when restarting either of staging and production so don't wander off and have a coffee while it runs...

```
./hint upgrade all
```

### Upgrade just hintr (i.e. naomi) part of hint

This will pull new containers, take down hintr and the workers, and bring up new copies.  User sessions will be unaffected and model runs that are part way through will be continued.  The `hintr` part of the app will be unavailable for ~10 s during this process.  Again, you will need to provide your github token part way through.

```
./hint upgrade hintr
```

## Simulate slow connections

For testing performance, connect the application to [toxiproxy](https://toxiproxy.io) by running

```
./scripts/slow
```

and then connect to http://localhost:8081

The bandwidth and latency of the connection will be affected - see `./scripts/slow --help` for details.

## Proxy & SSL

For now, we're going to use self-signed certificates for `naomi.dide.ic.ac.uk`, which we will replace with more reasonable certificates later.  Certificates are generated during start-up of the proxy container.

## License

MIT © Imperial College of Science, Technology and Medicine
