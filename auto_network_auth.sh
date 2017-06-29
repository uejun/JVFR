#!/bin/zsh

source $HOME/.zshrc > /dev/null 2>&1
cd /Users/uejun/sandbox/JVFR
export ENV_NAME=JVFR
export VIRTUALENV_PATH=/Users/uejun/myvirtualenv/$ENV_NAME
export PYTHON=$VIRTUALENV_PATH/bin/python
$PYTHON auto_network_auth.py
