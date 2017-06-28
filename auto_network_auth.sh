#!/bin/zsh

source /Users/uejun/.zshrc > /dev/null 2>&1
cd /Users/uejun/sandbox/try_selenium
export ENV_NAME=try_selenium
export VIRTUALENV_PATH=/Users/uejun/MyVirtualevnv/$ENV_NAME
export PYTHON=$VIRTUALENV_PATH/bin/python
$PYTHON auto_network_auth.py