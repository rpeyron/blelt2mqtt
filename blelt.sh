#!/bin/bash

MY_PWD="$( dirname -- "$( readlink -f -- "$0"; )" )";
{ python3 "$MY_PWD/ble-lt-thermometer.py" > "$MY_PWD/blelt.logs"; } 2>&1
