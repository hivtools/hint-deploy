# hint-deploy

[![Build Status](https://travis-ci.org/mrc-ide/hint-deploy.svg?branch=master)](https://travis-ci.com/mrc-ide/hint-deploy)
[![codecov.io](https://codecov.io/github/mrc-ide/hint-deploy/coverage.svg?branch=master)](https://codecov.io/github/mrc-ide/hint-deploy?branch=master)

Deployment scripts for [hint](https://github.com/mrc-ide/hint)

<!-- Regenerate the usage section below by running ./scripts/build_readme -->

<!-- Usage begin -->
```
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
```
<!-- Usage end -->

## License

MIT © Imperial College of Science, Technology and Medicine
