# hint-deploy

[![Build Status](https://travis-ci.org/mrc-ide/hint-deploy.svg?branch=master)](https://travis-ci.org/mrc-ide/hint-deploy)
[![codecov.io](https://codecov.io/github/mrc-ide/hint-deploy/coverage.svg?branch=master)](https://codecov.io/github/mrc-ide/hint-deploy?branch=master)

Deployment scripts for [hint](https://github.com/mrc-ide/hint)

<!-- Regenerate the usage section below by running ./scripts/build_readme -->

<!-- Usage begin -->
```
Usage:
  ./hint start [--pull]
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
```
<!-- Usage end -->

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
