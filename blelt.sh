#!/bin/bash


#MY_PWD="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
MY_PWD="$( dirname -- "$( readlink -f -- "$0"; )" )";


while true; do
sleep 30
{ python3 "$MY_PWD/blelt2mqtt.py" > "$MY_PWD/blelt2mqtt.log"; } 2>&1
done
