# hint-deploy

[![Build status](https://github.com/hint/hint-deploy/workflows/test/badge.svg)](https://github.com/hint/hint-deploy/actions)
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
  ./hint start [--pull] [--hintr-branch=<branch>] [--hint-branch=<branch>] [<configname>]
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
  --kill                    Kill the containers (faster, but possible db corruption)
  --hint-branch=<branch>    The hint branch to deploy
  --hintr-branch=<branch>   The hintr branch to deploy
```
<!-- Usage end -->

Once a configuration is set during `start`, it will be reused by subsequent commands (`stop`, `status`, `upgrade`, `user`, etc) and removed during `destroy`.  The configuration usage information is stored in `config/.last_deploy`.

## Testing

hint-deploy uses [AppRole](https://developer.hashicorp.com/vault/docs/auth/approle) to authenticate with the vault. To run tests locally you will need to set `VAULT_AUTH_ROLE_ID` and `VAULT_AUTH_SECRET_ID` to valid role-id and secret-it.

To get them run

```
vault login -method=github
VAULT_AUTH_ROLE_ID=$(vault read -field=role_id auth/approle/role/hint-deploy/role-id)
VAULT_AUTH_SECRET_ID=$(vault write --field=secret_id -f auth/approle/role/hint-deploy/secret-id)
```
ensure they are available as env vars wherever you run pytest from. These are available to the CI as repo secrets.

You can test it by trying to login via
```
vault write auth/approle/login role_id=$VAULT_AUTH_ROLE_ID secret_id=$VAULT_AUTH_SECRET_ID
```

## Deployment onto the servers

We have two copies of hint deployed:

- [production](https://naomi.dide.ic.ac.uk) is `https://naomi.dide.ic.ac.uk`
- [staging](https://naomi-staging.dide.ic.ac.uk) is `https://naomi-staging.dide.ic.ac.uk`

To get onto production, ssh to `naomi.dide` as the `hint` user with

```
ssh hint@naomi.dide.ic.ac.uk
```

your public key should be added to the `.ssh/authorized_users` file.

To get onto the staging server

```
ssh vagrant@naomi-staging.dide.ic.ac.uk
```

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
    - db (hint-db): running
    - redis (hint-redis): running
    - hintr (hint-hintr): running
    - hint (hint-hint): running
    - proxy (hint-proxy): running
    - worker (hint-worker_<i>): running (2)
```

The first line indicates the active configuration (see [`config/`](config)).  The number in brackets on the last line indicates the number of workers.  Hopefully everything else is self explanatory.

### Starting a copy of hint that has stopped

On machine reboot, hint will not restart automatically ([mrc-735](https://vimc.myjetbrains.com/youtrack/issue/mrc-735)), so you may need to start hint up with:

```
./hint start
```

if it has already been run you do not need to provide the instance name (staging or production) though adding it is harmless.  You will be prompted for your github token during startup.

If you are restarting hint after a machine reboot, some containers will still exist (though they are exited) and you will get an error like:

```
[Loaded configuration 'staging' (2 days ago)]
...
Exception: Some containers exist
```

in which case you should run `docker container prune` or `./hint stop` to remove the stopped containers and let you run `./hint start` again.

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

There are 3 options for ssl certificates

1. Self-signed certificates, which are generated in the proxy at startup (this is the default configuration option)
2. Certificates for `naomi.dide.ic.ac.uk`, provided by ICT (see [details on `reside-ic/proxy-nginx`](https://github.com/reside-ic/proxy-nginx#getting-a-certificate-from-ict)), stored in the mrc-ide vault
3. Certificates from UNAIDS

For the last option, UNAIDS will send a certificate.  Instructions are [on the leaderssl website](https://www.leaderssl.com/articles/131-certificate-installation-nginx)

First, concatenate the certificates:

```
cat naomi_unaids_org.crt  naomi_unaids_org.ca-bundle > ssl-bundle.crt
```

Then add them to the [mrc-ide vault](https://github.com/mrc-ide/vault):

```
export VAULT_ADDR=https://vault.dide.ic.ac.uk:8200
vault login -method=github
vault write /secret/hint/ssl/unaids certificate=@ssl-bundle.crt key=@naomi.key
```

The production configuration will read these in.

## Modifying deploy

By default `hint` will deploy with docker containers built off the `master` image. If you want to deploy using an image from a particular branch for testing you can do this by passing one of the args `--hintr-branch=<tag-name>` or `--hint-branch=<tag-name>` or by modifying the `tag` section `config/hint.yml` file.

Images available on the remote are tagged with
* `hintr` - branch name e.g. `mrc-745`, git hash e.g. `56c3b7f`, version number e.g. `v0.0.15`
* `hint`- branch name e.g. `mrc-745`, git hash e.g. `6125a71`


## License

MIT © Imperial College of Science, Technology and Medicine
