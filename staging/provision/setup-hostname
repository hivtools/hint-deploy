#!/usr/bin/env bash
set -e
NAME=$1
if [ ! "$#" -eq 1 ]; then
    echo "Expected one argument"
    exit 1
fi

hostname $NAME
sed -i "s/vagrant/$NAME/g" /etc/hosts
sed -i "s/vagrant/$NAME/g" /etc/hostname
