#!/bin/bash


#MY_PWD="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
MY_PWD="$( dirname -- "$( readlink -f -- "$0"; )" )";


while true; do
sleep 30
{ python3 "$MY_PWD/ble-lt-thermometer.py" > "$MY_PWD/blelt.logs"; } 2>&1
done
