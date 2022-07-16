#!/bin/bash


MY_PWD="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

while true; do
sleep 30
python3  $MY_PWD/ble-lt-thermometer.py 2>&1 > $MY_PWD/blelt.logs
done


