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

## License

MIT © Imperial College of Science, Technology and Medicine
