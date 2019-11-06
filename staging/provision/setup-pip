#!/usr/bin/env bash
set -x

if which -a pip3 > /dev/null; then
    echo "pip is already installed (for Python 3)"
else
    echo "installing pip (for Python 3)"
    sudo apt-get update
    sudo apt-get install -y python3-pip
    sudo pip3 install --upgrade pip
fi