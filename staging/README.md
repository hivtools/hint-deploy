## Staging server for hint

### Machine & boostrapping this whole process

Log in to the server

```
ssh hint@naomi.dide.ic.ac.uk
```

(if you need sudo on this machine, the password is in the vault (`vault.dide.ic.ac.uk:8200`) as `/secret/hint/server/login`

 (ebola2018.dide.ic.ac.uk), run the following commands.

```
git clone https://github.com/imperialebola2018/hint-deploy
```

### Requirements

Install [Vagrant](https://www.vagrantup.com/downloads.html) and [VirtualBox](https://www.virtualbox.org/wiki/Downloads) in the host machine, along with [Vault](https://www.vaultproject.io)

```
sudo ./hint-deploy/staging/provision/setup-vagrant
sudo ./hint-deploy/staging/provision/setup-vault
```

### Build the VM

```
(cd hint-deploy/staging; vagrant up)
cp hint-deploy/staging/scripts/ssh-staging ~
```

### Actual deployment

```
./ssh-staging
cd hint-deploy
./hint start --pull
```

after which hint will be available as http://naomi.dide.ic.ac.uk:8080
