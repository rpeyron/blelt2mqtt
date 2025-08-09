#!/bin/bash

MY_PWD="$( dirname -- "$( readlink -f -- "$0"; )" )";
{ python3 "$MY_PWD/blelt2mqtt.py" > "$MY_PWD/blelt2mqtt.log"; } 2>&1
